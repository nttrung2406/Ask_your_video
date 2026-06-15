from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from src.video_module.domain.models.video import VideoSession, PreprocessingResult


class CacheRepository(ABC):
    """Port for caching video sessions."""
    
    @abstractmethod
    async def save_session(self, session: VideoSession, ttl_seconds: int = 3600) -> None:
        """Save a video session to cache."""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[VideoSession]:
        """Get a video session from cache."""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a video session from cache."""
        pass
    
    @abstractmethod
    async def update_session(self, session: VideoSession, ttl_seconds: int = 3600) -> None:
        """Update an existing session in cache."""
        pass
    
    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """Check if a session exists in cache."""
        pass


class ModelServicePort(ABC):
    """Port for interacting with the model service."""
    
    @abstractmethod
    async def upload_video(self, file_path: str, session_id: str) -> Dict[str, Any]:
        """Upload a video to the model service."""
        pass
    
    @abstractmethod
    async def preprocess_video(self, video_path: str, session_id: str, vlm_prompt: Optional[str] = None) -> PreprocessingResult:
       
        pass
    
    @abstractmethod
    async def ask_question(self, session_id: str, question: str) -> Dict[str, Any]:
       
        pass
    
    @abstractmethod
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information from model service."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if model service is healthy."""
        pass


class FileStoragePort(ABC):
    """Port for file storage operations."""
    
    @abstractmethod
    async def save_file(self, file_content: bytes, filename: str, session_id: str) -> str:
        """Save a file and return the path."""
        pass
    
    @abstractmethod
    async def get_file_path(self, session_id: str, filename: str) -> Optional[str]:
        """Get the path to a stored file."""
        pass
    
    @abstractmethod
    async def delete_files(self, session_id: str) -> bool:
        """Delete all files for a session."""
        pass
