"""
LLM Processor Module
Handles reasoning using llama.cpp with DeepSeek model
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from loguru import logger

from pipeline.interface.llm_interfaces import ReasoningResult
from model_resource.config import DEEPSEEK_MODEL_PATH


class LLMProcessor:
    """
    Handles LLM reasoning using llama.cpp with DeepSeek model.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        llama_cpp_path: Optional[str] = None,
        context_size: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.9,
        n_threads: int = 4
    ):
        """
        Initialize LLM Processor.
        
        Args:
            model_path: Path to GGUF model file (defaults to DeepSeek model)
            llama_cpp_path: Path to llama.cpp installation
            context_size: Context window size
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            n_threads: Number of threads to use
        """
        self.model_path = model_path or os.environ.get(
            "LLAMA_MODEL_PATH", DEEPSEEK_MODEL_PATH
        )
        self.llama_cpp_path = llama_cpp_path or os.environ.get(
            "LLAMA_CPP_PATH", "/opt/llama.cpp"
        )
        self.context_size = context_size
        self.temperature = temperature
        self.top_p = top_p
        self.n_threads = n_threads
        
        # Try to use llama-cpp-python if available
        self._use_python_binding = False
        self._llm = None
        
    def _init_python_binding(self):
        """Initialize llama-cpp-python if available."""
        if self._llm is not None:
            return True
            
        try:
            from llama_cpp import Llama
            
            if not Path(self.model_path).exists():
                logger.warning(f"Model not found at {self.model_path}")
                return False
            
            logger.info(f"Loading LLM model: {self.model_path}")
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.context_size,
                n_threads=self.n_threads,
                verbose=False
            )
            self._use_python_binding = True
            logger.info("LLM model loaded via llama-cpp-python")
            return True
            
        except ImportError:
            logger.warning("llama-cpp-python not available, will use CLI")
            return False
        except Exception as e:
            logger.warning(f"Failed to load model with Python binding: {e}")
            return False
    
    def _run_with_cli(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Run inference using llama.cpp CLI.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        main_binary = Path(self.llama_cpp_path) / "main"
        
        if not main_binary.exists():
            raise RuntimeError(f"llama.cpp binary not found at {main_binary}")
        
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        
        # Write prompt to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name
        
        try:
            cmd = [
                str(main_binary),
                "-m", self.model_path,
                "-f", prompt_file,
                "-n", str(max_tokens),
                "-t", str(self.n_threads),
                "-c", str(self.context_size),
                "--temp", str(self.temperature),
                "--top-p", str(self.top_p),
                "--no-display-prompt"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"llama.cpp error: {result.stderr}")
                raise RuntimeError(f"Inference failed: {result.stderr}")
            
            return result.stdout.strip()
            
        finally:
            Path(prompt_file).unlink(missing_ok=True)
    
    def _run_with_python(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Run inference using llama-cpp-python.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        if not self._init_python_binding():
            raise RuntimeError("Failed to initialize Python binding")
        
        output = self._llm(
            prompt,
            max_tokens=max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            stop=["[/INST]", "</s>", "[END]"],
            echo=False
        )
        
        return output["choices"][0]["text"].strip()
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512
    ) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        # Try Python binding first, fall back to CLI
        if self._use_python_binding or self._init_python_binding():
            return self._run_with_python(prompt, max_tokens)
        else:
            return self._run_with_cli(prompt, max_tokens)
    
    def reason(
        self,
        timeline: str,
        question: str,
        max_tokens: int = 1024
    ) -> ReasoningResult:
        """
        Perform reasoning on video timeline.
        
        Args:
            timeline: Formatted video timeline text
            question: User question about the video
            max_tokens: Maximum tokens to generate
            
        Returns:
            ReasoningResult object
        """
        prompt = self._build_reasoning_prompt(timeline, question)
        
        logger.info("Running reasoning inference...")
        raw_output = self.generate(prompt, max_tokens)
        
        # Parse the output
        answer, thinking = self._parse_reasoning_output(raw_output)
        
        return ReasoningResult(
            question=question,
            answer=answer,
            thinking_process=thinking,
            raw_output=raw_output
        )
    
    def _build_reasoning_prompt(self, timeline: str, question: str) -> str:
        """Build the reasoning prompt."""
        prompt = f"""You are a video reasoning assistant. Below is a textual timeline representation of a short video. Analyze it carefully to answer the question.

[VIDEO TIMELINE]
{timeline}

[USER QUESTION]
{question}

[REASONING COMPONENT]
Let me analyze the video timeline step by step:

Thinking Process:"""
        
        return prompt
    
    def _parse_reasoning_output(self, output: str) -> tuple:
        """
        Parse reasoning output to extract answer and thinking process.
        
        Args:
            output: Raw model output
            
        Returns:
            Tuple of (answer, thinking_process)
        """
        # Try to separate thinking from answer
        thinking = None
        answer = output
        
        # Look for common delimiters
        delimiters = [
            "Final Answer:",
            "Answer:",
            "Conclusion:",
            "Therefore,",
            "In conclusion,"
        ]
        
        for delimiter in delimiters:
            if delimiter in output:
                parts = output.split(delimiter, 1)
                thinking = parts[0].strip()
                answer = parts[1].strip() if len(parts) > 1 else output
                break
        
        return answer, thinking
    
    def unload_model(self):
        """Unload model from memory."""
        if self._llm is not None:
            del self._llm
            self._llm = None
        logger.info("LLM model unloaded")


def reason_about_video(
    timeline: str,
    question: str,
    model_path: Optional[str] = None
) -> ReasoningResult:
    """
    Convenience function for video reasoning.
    
    Args:
        timeline: Formatted video timeline
        question: User question
        model_path: Path to model (optional)
        
    Returns:
        ReasoningResult object
    """
    processor = LLMProcessor(model_path=model_path)
    return processor.reason(timeline, question)
