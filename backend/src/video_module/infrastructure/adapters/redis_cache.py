import json
from typing import Optional
import redis.asyncio as redis
from loguru import logger

from src.video_module.domain.models.video import VideoSession
from src.video_module.domain.ports.video_ports import CacheRepository


class RedisCacheAdapter(CacheRepository):
    """Redis implementation of CacheRepository."""
    
    def __init__(self, redis_url: str = "redis://session-redis:6379"):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._prefix = "video_session:"
    
    @property
    def redis_client(self) -> Optional[redis.Redis]:
        """Expose the Redis client for other adapters."""
        return self._client
    
    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client
    
    async def close(self):
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
    
    def _key(self, session_id: str) -> str:
        """Generate Redis key for a session."""
        return f"{self._prefix}{session_id}"
    
    async def save_session(self, session: VideoSession, ttl_seconds: int = 3600) -> None:
        """Save a video session to Redis."""
        client = await self._get_client()
        key = self._key(session.id)
        data = json.dumps(session.to_dict())
        await client.setex(key, ttl_seconds, data)
        logger.debug(f"Saved session to Redis: {session.id}")
    
    async def get_session(self, session_id: str) -> Optional[VideoSession]:
        """Get a video session from Redis."""
        client = await self._get_client()
        key = self._key(session_id)
        data = await client.get(key)
        if data:
            return VideoSession.from_dict(json.loads(data))
        return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a video session from Redis."""
        client = await self._get_client()
        key = self._key(session_id)
        result = await client.delete(key)
        return result > 0
    
    async def update_session(self, session: VideoSession, ttl_seconds: int = 3600) -> None:
        """Update an existing session (same as save)."""
        await self.save_session(session, ttl_seconds)
    
    async def exists(self, session_id: str) -> bool:
        """Check if a session exists in Redis."""
        client = await self._get_client()
        key = self._key(session_id)
        return await client.exists(key) > 0
