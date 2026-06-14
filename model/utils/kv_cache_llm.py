import os
import json
import httpx
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from pipeline.interface.llm_interfaces import ReasoningResult


@dataclass
class KVCacheConfig:
    """Configuration for KV cache optimization."""
    server_url: str = "http://localhost:8080"
    cache_type_k: str = "q8_0"  # KV cache quantization for keys
    cache_type_v: str = "q8_0"  # KV cache quantization for values
    defrag_threshold: float = 0.1  # Defragmentation threshold
    slot_save_path: str = "/app/cache/slots"  # Path to save slot states
    enable_debug: bool = True  # Enable debug logging for cache hits


class KVCacheLLMProcessor:
    """
    LLM Processor with KV Cache support using llama.cpp server.
    
    Strategy:
    1. Load video timeline as the prefix (system prompt)
    2. Cache the prefix KV computations
    3. Send questions after the prefix for fast inference
    4. Monitor cache hits via debug slots
    """
    
    def __init__(
        self,
        server_url: str = "http://localhost:8080",
        model_path: Optional[str] = None,
        context_size: int = 8192,
        temperature: float = 0.6,
        max_tokens: int = 1024,
        config: Optional[KVCacheConfig] = None
    ):
        """
        Initialize KV Cache LLM Processor.
        
        Args:
            server_url: URL of the llama.cpp server
            model_path: Path to GGUF model (for standalone mode)
            context_size: Context window size
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            config: KV cache configuration
        """
        self.server_url = server_url.rstrip("/")
        self.model_path = model_path or os.environ.get(
            "LLAMA_MODEL_PATH",
            "/app/model_resource/DeepSeek-R1-Distill-Qwen-7B-Q3_K_M.gguf"
        )
        self.context_size = context_size
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.config = config or KVCacheConfig(server_url=server_url)
        
        # Session prefix cache mapping
        self._prefix_cache: Dict[str, str] = {}
        
        # HTTP client with longer timeout for inference
        self._client = httpx.Client(timeout=300.0)
        
        logger.info(f"KV Cache LLM initialized - Server: {self.server_url}")
    
    def _build_system_prompt(self, timeline_text: str) -> str:
        """Build the system prompt with video timeline as prefix."""
        return f"""You are a video reasoning assistant analyzing a video timeline. Below is a chronological timeline of the video content including visual descriptions and audio transcripts.

[VIDEO TIMELINE]
{timeline_text}

[END OF TIMELINE]

Based on this timeline, answer questions about the video content. Provide clear, detailed reasoning about what happens in the video."""
    
    def _build_reasoning_prompt(self, question: str) -> str:
        """Build the user question prompt."""
        return f"""[USER QUESTION]
{question}

[REASONING]
Let me analyze the video timeline to answer this question.

Thinking Process:"""
    
    def reason_with_cache(
        self,
        session_id: str,
        timeline_text: str,
        question: str
    ) -> ReasoningResult:
        """
        Perform reasoning with KV cache optimization.
        
        The timeline is cached as a prefix, subsequent questions
        reuse the cached KV computations.
        
        Args:
            session_id: Session identifier for cache slot
            timeline_text: Video timeline text (cached as prefix)
            question: User question
            
        Returns:
            ReasoningResult object
        """
        # Build the full prompt
        system_prompt = self._build_system_prompt(timeline_text)
        question_prompt = self._build_reasoning_prompt(question)
        
        # Check if this session's prefix is cached
        cache_key = f"{session_id}:{hash(timeline_text)}"
        is_cached = cache_key in self._prefix_cache
        
        if is_cached:
            logger.info(f"[KV Cache] Prefix cache HIT for session {session_id}")
        else:
            logger.info(f"[KV Cache] Prefix cache MISS for session {session_id} - caching prefix")
            self._prefix_cache[cache_key] = system_prompt
        
        # Build the messages for chat completion
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question_prompt}
        ]
        
        try:
            response = self._call_server(messages)
            
            # Parse reasoning output
            thinking_process, answer = self._parse_reasoning_output(response)
            
            return ReasoningResult(
                question=question,
                answer=answer,
                thinking_process=thinking_process,
                raw_output=response
            )
            
        except Exception as e:
            logger.error(f"KV Cache reasoning error: {e}")
            raise
    
    def _call_server(self, messages: list) -> str:
        """
        Call the llama.cpp server with chat completion.
        
        Uses the /v1/chat/completions endpoint which supports
        automatic prefix caching.
        """
        payload = {
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
            # Enable cache prompt for prefix reuse
            "cache_prompt": True
        }
        
        try:
            response = self._client.post(
                f"{self.server_url}/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Log cache statistics if available
            if "timings" in data:
                timings = data["timings"]
                if self.config.enable_debug:
                    logger.debug(f"[KV Cache Stats] prompt_n={timings.get('prompt_n', 'N/A')}, "
                               f"cache_n={timings.get('cached_n', 'N/A')}")
            
            return data["choices"][0]["message"]["content"]
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Server error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise
    
    def _call_completion(self, prompt: str) -> str:
        """
        Call the llama.cpp server with completion endpoint.
        Used as fallback for non-chat models.
        """
        payload = {
            "prompt": prompt,
            "temperature": self.temperature,
            "n_predict": self.max_tokens,
            "stream": False,
            "cache_prompt": True
        }
        
        try:
            response = self._client.post(
                f"{self.server_url}/completion",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Log cache statistics
            if self.config.enable_debug:
                logger.debug(f"[KV Cache Stats] tokens_cached={data.get('tokens_cached', 'N/A')}, "
                           f"timings={data.get('timings', {})}")
            
            return data["content"]
            
        except Exception as e:
            logger.error(f"Completion error: {e}")
            raise
    
    def _parse_reasoning_output(self, output: str) -> tuple:
        """
        Parse the LLM output into thinking process and answer.
        
        Returns:
            Tuple of (thinking_process, answer)
        """
        output = output.strip()
        
        # Look for answer delimiter
        answer_markers = ["Answer:", "Final Answer:", "Therefore:", "In conclusion:"]
        
        thinking_process = output
        answer = output
        
        for marker in answer_markers:
            if marker in output:
                parts = output.split(marker, 1)
                thinking_process = parts[0].strip()
                answer = parts[1].strip() if len(parts) > 1 else output
                break
        
        # If no marker found, use last paragraph as answer
        if thinking_process == answer:
            paragraphs = output.split("\n\n")
            if len(paragraphs) > 1:
                thinking_process = "\n\n".join(paragraphs[:-1])
                answer = paragraphs[-1]
        
        return thinking_process, answer
    
    def save_slot_state(self, session_id: str, slot_id: int = 0) -> bool:
        """
        Save the KV cache slot state to disk.
        Useful for persisting cache across server restarts.
        """
        try:
            save_path = Path(self.config.slot_save_path) / session_id
            save_path.mkdir(parents=True, exist_ok=True)
            
            response = self._client.post(
                f"{self.server_url}/slots/{slot_id}?action=save",
                json={"filepath": str(save_path / "slot.bin")}
            )
            response.raise_for_status()
            
            logger.info(f"Saved slot state for session {session_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to save slot state: {e}")
            return False
    
    def load_slot_state(self, session_id: str, slot_id: int = 0) -> bool:
        """Load a previously saved KV cache slot state."""
        try:
            slot_path = Path(self.config.slot_save_path) / session_id / "slot.bin"
            
            if not slot_path.exists():
                return False
            
            response = self._client.post(
                f"{self.server_url}/slots/{slot_id}?action=restore",
                json={"filepath": str(slot_path)}
            )
            response.raise_for_status()
            
            logger.info(f"Restored slot state for session {session_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load slot state: {e}")
            return False
    
    def check_server_health(self) -> Dict[str, Any]:
        """Check the llama.cpp server health and cache status."""
        try:
            response = self._client.get(f"{self.server_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_slots_info(self) -> Dict[str, Any]:
        """Get information about cache slots."""
        try:
            response = self._client.get(f"{self.server_url}/slots")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to get slots info: {e}")
            return {}
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def __del__(self):
        """Cleanup on destruction."""
        if hasattr(self, '_client'):
            self._client.close()


def get_llama_server_command(
    model_path: str,
    port: int = 8080,
    context_size: int = 8192,
    n_slots: int = 4,
    cache_type_k: str = "q8_0",
    cache_type_v: str = "q8_0",
    defrag_threshold: float = 0.1,
    n_gpu_layers: int = 0,
    enable_debug: bool = True
) -> str:
    """
    Generate the llama-server command with KV cache optimizations.
    
    Args:
        model_path: Path to the GGUF model
        port: Server port
        context_size: Context window size
        n_slots: Number of cache slots
        cache_type_k: KV cache type for keys (q8_0, q4_0, f16)
        cache_type_v: KV cache type for values (q8_0, q4_0, f16)
        defrag_threshold: Cache defragmentation threshold
        n_gpu_layers: GPU layers 
        enable_debug: Enable debug slot logging
        
    Returns:
        Command string to run llama-server
    """
    cmd_parts = [
        "llama-server",
        f"--model {model_path}",
        f"--port {port}",
        f"--ctx-size {context_size}",
        f"--parallel {n_slots}",  # Number of parallel slots
        f"--cache-type-k {cache_type_k}",
        f"--cache-type-v {cache_type_v}",
        f"--defrag-thold {defrag_threshold}",
        "--cont-batching",  # Enable continuous batching
        "--flash-attn",  # Enable flash attention if available
    ]
    
    if n_gpu_layers != 0:
        cmd_parts.append(f"--n-gpu-layers {n_gpu_layers}")
    
    if enable_debug:
        cmd_parts.append("--verbose")
    
    return " ".join(cmd_parts)
