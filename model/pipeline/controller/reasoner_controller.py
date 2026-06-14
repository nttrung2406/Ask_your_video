"""
Reasoner Controller - Phase 4
Performs reasoning over the aggregated timeline using LLM

Supports two modes:
1. Direct mode: Uses llama-cpp-python or CLI
2. Server mode: Uses llama-server with KV cache for efficient prefix caching
"""

import os
from typing import Optional
from loguru import logger

from utils.llm_processor import LLMProcessor
from pipeline.interface import (
    AggregatedTimeline,
    VideoReasoningResult,
    ReasoningResult
)
from pipeline.controller.aggregator_controller import AggregatorController


# Default DeepSeek model path
DEEPSEEK_MODEL_PATH = "/app/model_resource/DeepSeek-R1-Distill-Qwen-7B-Q3_K_M.gguf"

# LLM Server URL for KV cache mode
LLM_SERVER_URL = os.environ.get("LLM_SERVER_URL", "http://localhost:8080")


class ReasonerController:
    """
    Phase 4: Local Reasoning Controller
    
    Uses llama.cpp with DeepSeek model to perform reasoning over the video timeline.
    Supports KV cache optimization for repeated questions on the same video.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        context_size: int = 8192,
        temperature: float = 0.6,
        max_tokens: int = 1024,
        use_kv_cache_server: bool = True,
        server_url: Optional[str] = None
    ):
        """
        Initialize ReasonerController.
        
        Args:
            model_path: Path to GGUF model file (defaults to DeepSeek model)
            context_size: LLM context window size
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            use_kv_cache_server: Whether to use the KV cache server mode
            server_url: URL of the llama-server (for KV cache mode)
        """
        # Use DeepSeek model by default
        self.model_path = model_path or os.environ.get(
            "LLAMA_MODEL_PATH",
            DEEPSEEK_MODEL_PATH
        )
        self.context_size = context_size
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_kv_cache_server = use_kv_cache_server
        self.server_url = server_url or LLM_SERVER_URL
        
        # Initialize the appropriate processor
        self._kv_cache_llm = None
        self._llm_processor = None
        
        if self.use_kv_cache_server:
            self._init_kv_cache_processor()
        else:
            self._init_direct_processor()
        
        self.aggregator_controller = AggregatorController()
        
        logger.info(f"ReasonerController initialized - KV Cache Mode: {self.use_kv_cache_server}")
    
    def _init_kv_cache_processor(self):
        """Initialize the KV cache LLM processor."""
        try:
            from utils.kv_cache_llm import KVCacheLLMProcessor, KVCacheConfig
            
            config = KVCacheConfig(
                server_url=self.server_url,
                cache_type_k="q8_0",
                cache_type_v="q8_0",
                enable_debug=True
            )
            
            self._kv_cache_llm = KVCacheLLMProcessor(
                server_url=self.server_url,
                model_path=self.model_path,
                context_size=self.context_size,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                config=config
            )
            
            logger.info(f"KV Cache LLM initialized - Server: {self.server_url}")
            
        except Exception as e:
            logger.warning(f"Failed to init KV cache mode: {e}, falling back to direct mode")
            self.use_kv_cache_server = False
            self._init_direct_processor()
    
    def _init_direct_processor(self):
        """Initialize the direct LLM processor."""
        self._llm_processor = LLMProcessor(
            model_path=self.model_path,
            context_size=self.context_size,
            temperature=self.temperature
        )
        logger.info(f"Direct LLM processor initialized: {self.model_path}")
    
    def reason(
        self,
        timeline: AggregatedTimeline,
        question: str,
        session_id: Optional[str] = None,
        system_context: Optional[str] = None
    ) -> VideoReasoningResult:
        """
        Perform reasoning over video timeline.
        
        Args:
            timeline: Aggregated video timeline
            question: User question
            session_id: Session ID for KV cache slot management
            system_context: Optional additional context
            
        Returns:
            VideoReasoningResult object
        """
        logger.info("Phase 4: Running reasoning...")
        logger.info(f"Question: {question}")
        
        if self.use_kv_cache_server and self._kv_cache_llm:
            # Use KV cache server mode
            reasoning_result = self._kv_cache_llm.reason_with_cache(
                session_id=session_id or "default",
                timeline_text=timeline.timeline_text,
                question=question
            )
        else:
            # Use direct mode
            reasoning_result = self._llm_processor.reason(
                timeline.timeline_text,
                question,
                max_tokens=self.max_tokens
            )
        
        # Create video reasoning result
        result = VideoReasoningResult(
            question=question,
            answer=reasoning_result.answer,
            thinking_process=reasoning_result.thinking_process,
            timeline_summary=self._summarize_timeline(timeline)
        )
        
        logger.info("Phase 4 complete")
        return result
    
    def _summarize_timeline(self, timeline: AggregatedTimeline) -> str:
        """Create a brief summary of the timeline."""
        visual_count = sum(1 for e in timeline.entries if e.entry_type == "visual")
        audio_count = sum(1 for e in timeline.entries if e.entry_type == "audio")
        
        return (
            f"Video duration: {timeline.video_duration:.1f}s, "
            f"{visual_count} visual events, {audio_count} audio segments"
        )
    
    def reason_with_prompt(
        self,
        full_prompt: str
    ) -> ReasoningResult:
        """
        Run reasoning with a pre-built prompt.
        
        Args:
            full_prompt: Complete prompt including timeline and question
            
        Returns:
            ReasoningResult object
        """
        logger.info("Running reasoning with custom prompt...")
        
        if self._llm_processor:
            output = self._llm_processor.generate(full_prompt, self.max_tokens)
        else:
            output = "LLM processor not initialized"
        
        return ReasoningResult(
            question="",
            answer=output,
            thinking_process=None,
            raw_output=output
        )
    
    def unload_model(self):
        """Unload LLM from memory."""
        if self._llm_processor:
            self._llm_processor.unload_model()
        if self._kv_cache_llm:
            self._kv_cache_llm.close()


def reason_about_video(
    timeline: AggregatedTimeline,
    question: str,
    model_path: Optional[str] = None
) -> VideoReasoningResult:
    """
    Convenience function for video reasoning.
    
    Args:
        timeline: Aggregated video timeline
        question: User question
        model_path: Optional path to model (defaults to DeepSeek)
        
    Returns:
        VideoReasoningResult object
    """
    controller = ReasonerController(model_path=model_path)
    return controller.reason(timeline, question)
