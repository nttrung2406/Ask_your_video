from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import uuid


class VideoStatus(str, Enum):
    """Video processing status."""
    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    PREPROCESSED = "preprocessed"
    READY = "ready"
    ERROR = "error"


@dataclass
class VideoMeta:
    """Video metadata."""
    name: str
    size: int
    duration_sec: float
    width: int
    height: int
    transcoded: bool = False
    mime_type: str = "video/mp4"


@dataclass
class PreprocessingResult:
    """Result from model preprocessing."""
    audio_path: str
    frame_count: int
    video_info: Dict[str, Any]
    output_dir: str


@dataclass
class VideoSession:
    """Video session domain model."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    video_path: Optional[str] = None
    video_meta: Optional[VideoMeta] = None
    status: VideoStatus = VideoStatus.UPLOADED
    preprocessing_result: Optional[PreprocessingResult] = None
    model_session_id: Optional[str] = None  # Session ID from model service
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "video_path": self.video_path,
            "video_meta": {
                "name": self.video_meta.name,
                "size": self.video_meta.size,
                "duration_sec": self.video_meta.duration_sec,
                "width": self.video_meta.width,
                "height": self.video_meta.height,
                "transcoded": self.video_meta.transcoded,
                "mime_type": self.video_meta.mime_type,
            } if self.video_meta else None,
            "status": self.status.value,
            "preprocessing_result": {
                "audio_path": self.preprocessing_result.audio_path,
                "frame_count": self.preprocessing_result.frame_count,
                "video_info": self.preprocessing_result.video_info,
                "output_dir": self.preprocessing_result.output_dir,
            } if self.preprocessing_result else None,
            "model_session_id": self.model_session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoSession":
        """Create from dictionary."""
        video_meta = None
        if data.get("video_meta"):
            vm = data["video_meta"]
            video_meta = VideoMeta(
                name=vm["name"],
                size=vm["size"],
                duration_sec=vm["duration_sec"],
                width=vm["width"],
                height=vm["height"],
                transcoded=vm.get("transcoded", False),
                mime_type=vm.get("mime_type", "video/mp4"),
            )
        
        preprocessing_result = None
        if data.get("preprocessing_result"):
            pr = data["preprocessing_result"]
            preprocessing_result = PreprocessingResult(
                audio_path=pr["audio_path"],
                frame_count=pr["frame_count"],
                video_info=pr["video_info"],
                output_dir=pr["output_dir"],
            )
        
        return cls(
            id=data["id"],
            video_path=data.get("video_path"),
            video_meta=video_meta,
            status=VideoStatus(data.get("status", "uploaded")),
            preprocessing_result=preprocessing_result,
            model_session_id=data.get("model_session_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            error_message=data.get("error_message"),
        )
