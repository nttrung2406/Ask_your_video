"""
Reasoning Module Ports (Interfaces)
Defines the contracts for the reasoning module.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from src.reasoning_module.domain.models.reasoning import (
    ReasoningQuestion,
    ReasoningAnswer,
    ReasoningSession,
    CacheStats
)


class ReasoningServicePort(ABC):
    """Port for the reasoning model service."""
    
    @abstractmethod
    async def ask_question(
        self,
        session_id: str,
        question: str,
    ) -> ReasoningAnswer:
        """
        Ask a question about a preprocessed video.
        
        Args:
            session_id: Session ID from video preprocessing
            question: The question to answer
            
        Returns:
            ReasoningAnswer object
        """
        pass
    
    @abstractmethod
    async def get_timeline_text(self, session_id: str) -> Optional[str]:
        """
        Get the cached timeline text for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Timeline text or None if not available
        """
        pass
    
    @abstractmethod
    async def get_cache_stats(self, session_id: str) -> CacheStats:
        """
        Get KV cache statistics for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            CacheStats object
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the reasoning service is healthy."""
        pass


class VideoSessionPort(ABC):
    """Port for accessing video session data."""
    
    @abstractmethod
    async def get_session_status(self, session_id: str) -> Optional[str]:
        """Get the status of a video session."""
        pass
    
    @abstractmethod
    async def is_preprocessed(self, session_id: str) -> bool:
        """Check if a video session is preprocessed and ready for reasoning."""
        pass
    
    @abstractmethod
    async def get_timeline_path(self, session_id: str) -> Optional[str]:
        """Get the path to the timeline text file for a session."""
        pass


class ReasoningCachePort(ABC):
    """Port for reasoning session cache."""
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[ReasoningSession]:
        """Get a reasoning session by ID."""
        pass
    
    @abstractmethod
    async def save_session(self, session: ReasoningSession, ttl_seconds: int) -> None:
        """Save a reasoning session."""
        pass
    
    @abstractmethod
    async def update_session(self, session: ReasoningSession, ttl_seconds: int) -> None:
        """Update a reasoning session."""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a reasoning session."""
        pass
