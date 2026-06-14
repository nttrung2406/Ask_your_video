"""
Reasoning Application Service
Orchestrates reasoning operations for video Q&A.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from src.reasoning_module.domain.models.reasoning import (
    ReasoningQuestion,
    ReasoningAnswer,
    ReasoningSession,
    ReasoningStatus,
    CacheStats
)
from src.reasoning_module.domain.ports.reasoning_ports import (
    ReasoningServicePort,
    VideoSessionPort,
    ReasoningCachePort
)


class ReasoningService:
    """
    Application service for video reasoning.
    
    Orchestrates the reasoning process:
    1. Validates video session is preprocessed
    2. Retrieves or loads timeline text
    3. Sends question to model service with KV cache
    4. Returns structured answer
    """
    
    def __init__(
        self,
        reasoning_service: ReasoningServicePort,
        video_session: VideoSessionPort,
        cache_repository: ReasoningCachePort,
        cache_ttl_seconds: int = 3600 * 24  # 24 hours
    ):
        """
        Initialize the reasoning service.
        
        Args:
            reasoning_service: Port to the reasoning model service
            video_session: Port to access video session data
            cache_repository: Port to cache reasoning sessions
            cache_ttl_seconds: TTL for cached sessions
        """
        self.reasoning_service = reasoning_service
        self.video_session = video_session
        self.cache = cache_repository
        self.cache_ttl = cache_ttl_seconds
    
    async def ask_question(
        self,
        session_id: str,
        question: str,
        vlm_prompt: Optional[str] = None
    ) -> ReasoningAnswer:
        """
        Ask a question about a preprocessed video.
        
        Args:
            session_id: Video session ID
            question: The question to answer
            vlm_prompt: Optional custom VLM prompt
            
        Returns:
            ReasoningAnswer object
            
        Raises:
            ValueError: If session not found or not preprocessed
        """
        logger.info(f"Processing question for session {session_id}: {question[:50]}...")
        
        start_time = datetime.utcnow()
        
        # Check if video session is ready
        is_ready = await self.video_session.is_preprocessed(session_id)
        if not is_ready:
            status = await self.video_session.get_session_status(session_id)
            raise ValueError(
                f"Video session not ready for reasoning. Status: {status or 'not found'}"
            )
        
        # Get or create reasoning session
        reasoning_session = await self._get_or_create_reasoning_session(session_id)
        
        try:
            # Update status to processing
            reasoning_session.status = ReasoningStatus.PROCESSING
            reasoning_session.updated_at = datetime.utcnow()
            await self.cache.update_session(reasoning_session, self.cache_ttl)
            
            # Call the reasoning service
            answer = await self.reasoning_service.ask_question(
                session_id=session_id,
                question=question,
                vlm_prompt=vlm_prompt
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            answer.processing_time = processing_time
            
            # Update session status
            reasoning_session.status = ReasoningStatus.COMPLETED
            reasoning_session.is_timeline_cached = True
            reasoning_session.updated_at = datetime.utcnow()
            await self.cache.update_session(reasoning_session, self.cache_ttl)
            
            logger.info(
                f"Question answered in {processing_time:.2f}s "
                f"(cache_hit={answer.cache_hit})"
            )
            
            return answer
            
        except Exception as e:
            # Update session with error
            reasoning_session.status = ReasoningStatus.ERROR
            reasoning_session.error_message = str(e)
            reasoning_session.updated_at = datetime.utcnow()
            await self.cache.update_session(reasoning_session, self.cache_ttl)
            
            logger.error(f"Reasoning failed for session {session_id}: {e}")
            raise
    
    async def _get_or_create_reasoning_session(
        self,
        video_session_id: str
    ) -> ReasoningSession:
        """Get existing reasoning session or create new one."""
        session = await self.cache.get_session(video_session_id)
        
        if session is None:
            # Get timeline path from video session
            timeline_path = await self.video_session.get_timeline_path(video_session_id)
            
            session = ReasoningSession(
                id=video_session_id,
                video_session_id=video_session_id,
                timeline_text_path=timeline_path,
                status=ReasoningStatus.PENDING
            )
            await self.cache.save_session(session, self.cache_ttl)
            logger.info(f"Created new reasoning session: {video_session_id}")
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[ReasoningSession]:
        """Get a reasoning session by ID."""
        return await self.cache.get_session(session_id)
    
    async def get_timeline_text(self, session_id: str) -> Optional[str]:
        """Get the timeline text for a session."""
        return await self.reasoning_service.get_timeline_text(session_id)
    
    async def get_cache_stats(self, session_id: str) -> CacheStats:
        """Get KV cache statistics for a session."""
        return await self.reasoning_service.get_cache_stats(session_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of reasoning service."""
        model_healthy = await self.reasoning_service.health_check()
        
        return {
            "status": "healthy" if model_healthy else "degraded",
            "model_service": "healthy" if model_healthy else "unhealthy"
        }
