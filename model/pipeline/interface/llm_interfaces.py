"""
LLM Interfaces
Dataclasses for LLM reasoning
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReasoningResult:
    """Result from the reasoning model."""
    question: str
    answer: str
    thinking_process: Optional[str] = None
    raw_output: str = ""
    
    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "thinking_process": self.thinking_process,
            "raw_output": self.raw_output
        }
