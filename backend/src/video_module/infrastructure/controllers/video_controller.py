from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field
from loguru import logger

from src.video_module.domain.models.video import VideoMeta, VideoStatus
from src.video_module.application.services.video_service import VideoService


router = APIRouter(prefix="/api/video", tags=["video"])

# Will be injected by main.py
video_service: Optional[VideoService] = None


def set_video_service(service: VideoService):
    """Set the video service instance (called from main.py)."""
    global video_service
    video_service = service


async def _preprocess_in_background(session_id: str):
    """Wrapper for background preprocessing with error handling."""
    try:
        logger.info(f"Starting background preprocessing for session: {session_id}")
        await video_service.preprocess_video(session_id)
        logger.info(f"Background preprocessing completed for session: {session_id}")
    except Exception as e:
        logger.error(f"Background preprocessing failed for session {session_id}: {e}")
        # Error is already saved to session by video_service.preprocess_video


# Request/Response Models
class VideoMetaRequest(BaseModel):
    """Video metadata from frontend."""
    name: str
    size: int
    duration_sec: float = Field(alias="durationSec")
    width: int
    height: int
    transcoded: bool = False
    
    class Config:
        populate_by_name = True


class UploadResponse(BaseModel):
    """Response after uploading a video."""
    session_id: str
    status: str
    message: str


class PreprocessResponse(BaseModel):
    """Response after preprocessing."""
    session_id: str
    status: str
    frame_count: Optional[int] = None
    audio_path: Optional[str] = None
    message: str


class SessionResponse(BaseModel):
    """Session information response."""
    session_id: str
    status: str
    video_name: Optional[str] = None
    video_size: Optional[int] = None
    is_preprocessed: bool
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_service: str
    cache: str


# Endpoints
@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    name: str = Form(...),
    size: int = Form(...),
    duration_sec: float = Form(..., alias="durationSec"),
    width: int = Form(...),
    height: int = Form(...),
    transcoded: bool = Form(False),
    auto_preprocess: bool = Form(True),
):
    """
    Upload a video file.
    If auto_preprocess is True, preprocessing starts in background.
    """
    if video_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Create VideoMeta
        meta = VideoMeta(
            name=name,
            size=size,
            duration_sec=duration_sec,
            width=width,
            height=height,
            transcoded=transcoded,
        )
        
        # Read file content
        content = await file.read()
        
        # Create session ID if not provided
        import uuid
        sid = session_id or str(uuid.uuid4())
        
        # Upload video
        session = await video_service.upload_video(
            session_id=sid,
            file_content=content,
            filename=file.filename or name,
            meta=meta,
        )
        
        # Start preprocessing in background if requested
        if auto_preprocess:
            background_tasks.add_task(_preprocess_in_background, sid)
            message = "Video uploaded, preprocessing started"
        else:
            message = "Video uploaded successfully"
        
        return UploadResponse(
            session_id=session.id,
            status=session.status.value,
            message=message,
        )
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preprocess/{session_id}", response_model=PreprocessResponse)
async def preprocess_video(session_id: str):
    """Manually trigger preprocessing for an uploaded video."""
    if video_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        session = await video_service.preprocess_video(session_id)
        
        return PreprocessResponse(
            session_id=session.id,
            status=session.status.value,
            frame_count=session.preprocessing_result.frame_count if session.preprocessing_result else None,
            audio_path=session.preprocessing_result.audio_path if session.preprocessing_result else None,
            message="Preprocessing completed",
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Preprocessing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session information."""
    if video_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    session = await video_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    return SessionResponse(
        session_id=session.id,
        status=session.status.value,
        video_name=session.video_meta.name if session.video_meta else None,
        video_size=session.video_meta.size if session.video_meta else None,
        is_preprocessed=session.status in [VideoStatus.PREPROCESSED, VideoStatus.READY],
        error_message=session.error_message,
    )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its files."""
    if video_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    deleted = await video_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    return {"status": "deleted", "session_id": session_id}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if video_service is None:
        return HealthResponse(
            status="unhealthy",
            model_service="unknown",
            cache="unknown",
        )
    
    health = await video_service.health_check()
    return HealthResponse(**health)
