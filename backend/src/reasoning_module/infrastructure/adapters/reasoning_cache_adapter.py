import json
from typing import Optional
from datetime import datetime
from loguru import logger

from src.reasoning_module.domain.models.reasoning import (
    ReasoningSession,
    ReasoningStatus
)
from src.reasoning_module.domain.ports.reasoning_ports import ReasoningCachePort


class ReasoningCacheAdapter(ReasoningCachePort):
    """
    Redis-based cache adapter for reasoning sessions.
    
    Uses the same Redis instance as the video module but with
    a different key prefix to avoid collisions.
    """
    
    KEY_PREFIX = "reasoning:session:"
    
    def __init__(self, redis_client):
        """
        Initialize the adapter.
        
        Args:
            redis_client: Async Redis client instance
        """
        self.redis = redis_client
    
    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for a session."""
        return f"{self.KEY_PREFIX}{session_id}"
    
    def _serialize_session(self, session: ReasoningSession) -> str:
        """Serialize a session to JSON."""
        data = {
            "id": session.id,
            "video_session_id": session.video_session_id,
            "timeline_text_path": session.timeline_text_path,
            "timeline_text": session.timeline_text,
            "is_timeline_cached": session.is_timeline_cached,
            "status": session.status.value,
            "error_message": session.error_message,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }
        return json.dumps(data)
    
    def _deserialize_session(self, data: str) -> ReasoningSession:
        """Deserialize a session from JSON."""
        obj = json.loads(data)
        return ReasoningSession(
            id=obj["id"],
            video_session_id=obj["video_session_id"],
            timeline_text_path=obj.get("timeline_text_path"),
            timeline_text=obj.get("timeline_text"),
            is_timeline_cached=obj.get("is_timeline_cached", False),
            status=ReasoningStatus(obj.get("status", "pending")),
            error_message=obj.get("error_message"),
            created_at=datetime.fromisoformat(obj["created_at"]),
            updated_at=datetime.fromisoformat(obj["updated_at"])
        )
    
    async def get_session(self, session_id: str) -> Optional[ReasoningSession]:
        """Get a reasoning session by ID."""
        try:
            key = self._session_key(session_id)
            data = await self.redis.get(key)
            
            if data is None:
                return None
            
            return self._deserialize_session(data)
            
        except Exception as e:
            logger.error(f"Failed to get reasoning session {session_id}: {e}")
            return None
    
    async def save_session(self, session: ReasoningSession, ttl_seconds: int) -> None:
        """Save a reasoning session."""
        try:
            key = self._session_key(session.id)
            data = self._serialize_session(session)
            
            await self.redis.setex(key, ttl_seconds, data)
            logger.debug(f"Saved reasoning session: {session.id}")
            
        except Exception as e:
            logger.error(f"Failed to save reasoning session {session.id}: {e}")
            raise
    
    async def update_session(self, session: ReasoningSession, ttl_seconds: int) -> None:
        """Update a reasoning session."""
        # For Redis, update is the same as save
        await self.save_session(session, ttl_seconds)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a reasoning session."""
        try:
            key = self._session_key(session_id)
            result = await self.redis.delete(key)
            
            if result > 0:
                logger.info(f"Deleted reasoning session: {session_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete reasoning session {session_id}: {e}")
            return False
