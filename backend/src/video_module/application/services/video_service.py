from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from src.video_module.domain.models.video import VideoSession, VideoStatus, VideoMeta
from src.video_module.domain.ports.video_ports import CacheRepository, ModelServicePort, FileStoragePort


class VideoService:
    """Application service for video processing orchestration."""
    
    def __init__(
        self,
        cache_repository: CacheRepository,
        model_service: ModelServicePort,
        file_storage: FileStoragePort,
        cache_ttl_seconds: int = 3600 * 24,  # 24 hours default
    ):
        self.cache = cache_repository
        self.model_service = model_service
        self.file_storage = file_storage
        self.cache_ttl = cache_ttl_seconds
    
    async def create_session(self) -> VideoSession:
        """Create a new video session."""
        session = VideoSession()
        await self.cache.save_session(session, self.cache_ttl)
        logger.info(f"Created new session: {session.id}")
        return session
    
    async def upload_video(
        self,
        session_id: str,
        file_content: bytes,
        filename: str,
        meta: VideoMeta,
    ) -> VideoSession:
        """Upload a video file and update the session."""
        # Get existing session or create new one
        session = await self.cache.get_session(session_id)
        if not session:
            session = VideoSession(id=session_id)
        
        # Save file locally first
        file_path = await self.file_storage.save_file(file_content, filename, session_id)
        
        # Update session
        session.video_path = file_path
        session.video_meta = meta
        session.status = VideoStatus.UPLOADED
        session.updated_at = datetime.utcnow()
        
        await self.cache.save_session(session, self.cache_ttl)
        logger.info(f"Video uploaded for session {session_id}: {filename}")
        
        return session
    
    async def preprocess_video(self, session_id: str) -> VideoSession:
        """Preprocess a video using the model service."""
        session = await self.cache.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        if not session.video_path:
            raise ValueError(f"No video uploaded for session: {session_id}")
        
        # Update status
        session.status = VideoStatus.PREPROCESSING
        session.updated_at = datetime.utcnow()
        await self.cache.update_session(session, self.cache_ttl)
        
        try:
            # Call model service to preprocess
            result = await self.model_service.preprocess_video(
                video_path=session.video_path,
                session_id=session_id,
            )
            
            # Update session with preprocessing result
            session.preprocessing_result = result
            session.model_session_id = session_id  # Model uses same session ID
            session.status = VideoStatus.PREPROCESSED
            session.updated_at = datetime.utcnow()
            
            await self.cache.update_session(session, self.cache_ttl)
            logger.info(f"Video preprocessed for session {session_id}")
            
            return session
            
        except Exception as e:
            session.status = VideoStatus.ERROR
            session.error_message = str(e)
            session.updated_at = datetime.utcnow()
            await self.cache.update_session(session, self.cache_ttl)
            logger.error(f"Preprocessing failed for session {session_id}: {e}")
            raise
    
    async def upload_and_preprocess(
        self,
        session_id: str,
        file_content: bytes,
        filename: str,
        meta: VideoMeta,
    ) -> VideoSession:
        """Upload video and immediately preprocess it."""
        # Upload first
        session = await self.upload_video(session_id, file_content, filename, meta)
        
        # Then preprocess
        session = await self.preprocess_video(session_id)
        
        return session
    
    async def ask_question(
        self,
        session_id: str,
        question: str,
    ) -> Dict[str, Any]:
        """Ask a question about a preprocessed video."""
        session = await self.cache.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        if session.status not in [VideoStatus.PREPROCESSED, VideoStatus.READY]:
            raise ValueError(f"Video not preprocessed. Current status: {session.status}")
        
        # Call model service
        result = await self.model_service.ask_question(
            session_id=session.model_session_id or session_id,
            question=question,
        )
        
        # Update session status
        session.status = VideoStatus.READY
        session.updated_at = datetime.utcnow()
        await self.cache.update_session(session, self.cache_ttl)
        
        return result
    
    async def get_session(self, session_id: str) -> Optional[VideoSession]:
        """Get a session by ID."""
        return await self.cache.get_session(session_id)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its files."""
        session = await self.cache.get_session(session_id)
        if session:
            await self.file_storage.delete_files(session_id)
            await self.cache.delete_session(session_id)
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all services."""
        model_healthy = await self.model_service.health_check()
        cache_healthy = await self.cache.exists("__health_check__") or True  # Cache is OK if accessible
        
        return {
            "status": "healthy" if model_healthy and cache_healthy else "degraded",
            "model_service": "healthy" if model_healthy else "unhealthy",
            "cache": "healthy" if cache_healthy else "unhealthy",
        }
