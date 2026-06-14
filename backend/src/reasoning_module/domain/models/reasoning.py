"""
Reasoning Module Domain Models
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class ReasoningStatus(str, Enum):
    """Status of a reasoning request."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ReasoningQuestion:
    """A question to be answered about a video."""
    question: str
    session_id: str
    vlm_prompt: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "session_id": self.session_id,
            "vlm_prompt": self.vlm_prompt,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ReasoningAnswer:
    """Answer from the reasoning model."""
    session_id: str
    question: str
    answer: str
    thinking_process: Optional[str] = None
    timeline_summary: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    cache_hit: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "question": self.question,
            "answer": self.answer,
            "thinking_process": self.thinking_process,
            "timeline_summary": self.timeline_summary,
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "cache_hit": self.cache_hit,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ReasoningSession:
    """A reasoning session for a video."""
    id: str
    video_session_id: str  # Reference to the video module session
    timeline_text_path: Optional[str] = None
    timeline_text: Optional[str] = None
    is_timeline_cached: bool = False
    status: ReasoningStatus = ReasoningStatus.PENDING
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "video_session_id": self.video_session_id,
            "timeline_text_path": self.timeline_text_path,
            "is_timeline_cached": self.is_timeline_cached,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class CacheStats:
    """Statistics about KV cache usage."""
    prompt_tokens: int = 0
    cached_tokens: int = 0
    cache_hit_ratio: float = 0.0
    total_requests: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "cached_tokens": self.cached_tokens,
            "cache_hit_ratio": self.cache_hit_ratio,
            "total_requests": self.total_requests
        }
