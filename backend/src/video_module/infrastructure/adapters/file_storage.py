import os
import shutil
from pathlib import Path
from typing import Optional
import aiofiles
from loguru import logger

from src.video_module.domain.ports.video_ports import FileStoragePort


class LocalFileStorageAdapter(FileStoragePort):
    """Local filesystem implementation of FileStoragePort."""
    
    def __init__(self, base_path: str = "/app/uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _session_dir(self, session_id: str) -> Path:
        """Get the directory for a session."""
        return self.base_path / session_id
    
    async def save_file(self, file_content: bytes, filename: str, session_id: str) -> str:
        """Save a file and return the path."""
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = session_dir / filename
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        
        logger.info(f"Saved file: {file_path}")
        return str(file_path)
    
    async def get_file_path(self, session_id: str, filename: str) -> Optional[str]:
        """Get the path to a stored file."""
        file_path = self._session_dir(session_id) / filename
        if file_path.exists():
            return str(file_path)
        return None
    
    async def delete_files(self, session_id: str) -> bool:
        """Delete all files for a session."""
        session_dir = self._session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
            logger.info(f"Deleted files for session: {session_id}")
            return True
        return False
