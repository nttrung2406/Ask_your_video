from typing import Optional
from loguru import logger

from src.reasoning_module.domain.ports.reasoning_ports import VideoSessionPort
from src.video_module.application.services.video_service import VideoService
from src.video_module.domain.models.video import VideoStatus


class VideoSessionAdapter(VideoSessionPort):
    """
    Adapter to access video session data from the video module.
    
    This adapter connects the reasoning module to the video module
    following hexagonal architecture principles.
    """
    
    def __init__(self, video_service: VideoService):
        """
        Initialize the adapter.
        
        Args:
            video_service: Video service instance from video module
        """
        self.video_service = video_service
    
    async def get_session_status(self, session_id: str) -> Optional[str]:
        """Get the status of a video session."""
        session = await self.video_service.get_session(session_id)
        
        if session is None:
            return None
        
        return session.status.value
    
    async def is_preprocessed(self, session_id: str) -> bool:
        """Check if a video session is preprocessed and ready for reasoning."""
        session = await self.video_service.get_session(session_id)
        
        if session is None:
            return False
        
        return session.status in [VideoStatus.PREPROCESSED, VideoStatus.READY]
    
    async def get_timeline_path(self, session_id: str) -> Optional[str]:
        """
        Get the path to the timeline text file for a session.
        
        The timeline file is saved by the model service during preprocessing
        at: /app/uploads/{session_id}/{video_name}_text_version.txt
        """
        session = await self.video_service.get_session(session_id)
        
        if session is None:
            return None
        
        # Construct the timeline path based on video path
        if session.video_path:
            import os
            video_dir = os.path.dirname(session.video_path)
            video_name = os.path.splitext(os.path.basename(session.video_path))[0]
            timeline_path = os.path.join(video_dir, f"{video_name}_text_version.txt")
            
            if os.path.exists(timeline_path):
                return timeline_path
        
        return None
