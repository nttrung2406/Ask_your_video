import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import aiofiles
from loguru import logger

from pipeline.controller.pipeline_controller import PipelineController
from pipeline.interface import (
    PipelineConfig,
)


# Global pipeline instance
pipeline: Optional[PipelineController] = None

# Session storage for preprocessed videos
sessions: Dict[str, Dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global pipeline
    logger.info("Starting Video Reasoning API Server (DeepSeek)...")
    
    config = PipelineConfig.from_env()
    pipeline = PipelineController(config)
    
    logger.info("Pipeline initialized")
    yield
    
    logger.info("Shutting down...")
    if pipeline:
        pipeline.cleanup()


app = FastAPI(
    title="Video Reasoning API",
    description="Multimodal Video Reasoning Pipeline API with DeepSeek",
    version="1.0.0",
    lifespan=lifespan
)


# Request/Response Models
class ProcessVideoRequest(BaseModel):
    """Request to process a video."""
    video_path: str = Field(..., description="Path to video file")
    question: str = Field(..., description="Question about the video")
    session_id: Optional[str] = Field(None, description="Optional session ID")
    vlm_prompt: Optional[str] = Field(None, description="Custom VLM prompt")


class ProcessVideoResponse(BaseModel):
    """Response from video processing."""
    session_id: str
    question: str
    answer: str
    thinking_process: Optional[str]
    timeline_text: str
    processing_time: float


class PreprocessRequest(BaseModel):
    """Request to preprocess a video."""
    video_path: str
    session_id: Optional[str] = None


class PreprocessResponse(BaseModel):
    """Response from preprocessing."""
    session_id: str
    video_path: str
    audio_path: str
    frame_count: int
    video_info: dict
    output_dir: str


class AskQuestionRequest(BaseModel):
    """Request to ask a question about a preprocessed video."""
    session_id: str
    question: str
    vlm_prompt: Optional[str] = None


class AskQuestionResponse(BaseModel):
    """Response to a question."""
    session_id: str
    question: str
    answer: str
    thinking_process: Optional[str]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    pipeline_ready: bool


# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        pipeline_ready=pipeline is not None
    )


@app.post("/process", response_model=ProcessVideoResponse)
async def process_video(request: ProcessVideoRequest):
    """
    Process a video and answer a question.
    This runs the complete pipeline.
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    video_path = Path(request.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {request.video_path}")
    
    try:
        # Run pipeline in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: pipeline.run(
                video_path=str(video_path),
                question=request.question,
                session_id=request.session_id,
                custom_vlm_prompt=request.vlm_prompt
            )
        )
        
        return ProcessVideoResponse(
            session_id=result.session_id,
            question=result.question,
            answer=result.answer,
            thinking_process=result.thinking_process,
            timeline_text=result.timeline_text,
            processing_time=result.processing_time
        )
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/preprocess", response_model=PreprocessResponse)
async def preprocess_video(request: PreprocessRequest):
    """
    Preprocess a video without asking a question.
    This extracts audio and keyframes for later use.
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    video_path = Path(request.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {request.video_path}")
    
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: pipeline.preprocess_only(str(video_path), session_id)
        )
        
        # Store session data
        sessions[session_id] = {
            "preprocessing_result": result,
            "translation_result": None,
            "timeline": None
        }
        
        return PreprocessResponse(
            session_id=session_id,
            video_path=str(video_path),
            audio_path=result.audio_path,
            frame_count=len(result.frames),
            video_info=result.video_info,
            output_dir=result.output_dir
        )
        
    except Exception as e:
        logger.error(f"Preprocessing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _save_timeline_text_file(session_id: str, video_path: str, timeline_text: str) -> str:
    """Save timeline text to uploads directory for caching."""
    video_name = Path(video_path).stem
    # Save to the same directory as the video
    upload_dir = Path("/app/data/uploads") / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    text_file_path = upload_dir / f"{video_name}_text_version.txt"
    
    with open(text_file_path, 'w', encoding='utf-8') as f:
        f.write(timeline_text)
    
    logger.info(f"Saved timeline text to: {text_file_path}")
    return str(text_file_path)


@app.post("/ask", response_model=AskQuestionResponse)
async def ask_question(request: AskQuestionRequest):
    """
    Ask a question about a preprocessed video.
    Requires a valid session_id from preprocessing.
    Uses KV cache for efficient repeated questioning.
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")
    
    session = sessions[request.session_id]
    preprocessing_result = session["preprocessing_result"]
    
    try:
        loop = asyncio.get_event_loop()
        
        # Run translation if not already done
        if session["translation_result"] is None:
            translation_result = await loop.run_in_executor(
                None,
                lambda: pipeline.translate_only(
                    preprocessing_result,
                    custom_vlm_prompt=request.vlm_prompt
                )
            )
            session["translation_result"] = translation_result
            
            # Aggregate timeline
            timeline = pipeline.aggregator.aggregate(
                translation_result.audio_segments,
                translation_result.frame_captions,
                preprocessing_result.video_info.get("duration")
            )
            session["timeline"] = timeline
            
            # Save timeline text file for caching
            text_file_path = _save_timeline_text_file(
                request.session_id,
                preprocessing_result.video_path,
                timeline.timeline_text
            )
            session["timeline_text_path"] = text_file_path
        
        timeline = session["timeline"]
        
        # Run reasoning with KV cache support
        reasoning_result = await loop.run_in_executor(
            None,
            lambda: pipeline.reason_only(timeline, request.question)
        )
        
        return AskQuestionResponse(
            session_id=request.session_id,
            question=request.question,
            answer=reasoning_result.answer,
            thinking_process=reasoning_result.thinking_process
        )
        
    except Exception as e:
        logger.error(f"Question error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    """
    Upload a video file for processing.
    Returns the path where the file was saved.
    """
    session_id = session_id or str(uuid.uuid4())
    
    # Create upload directory
    upload_dir = Path("/app/data/uploads") / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        return {
            "session_id": session_id,
            "file_path": str(file_path),
            "filename": file.filename,
            "size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session information."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    session = sessions[session_id]
    
    return {
        "session_id": session_id,
        "has_preprocessing": session["preprocessing_result"] is not None,
        "has_translation": session["translation_result"] is not None,
        "has_timeline": session["timeline"] is not None
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its data."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    
    raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")


@app.get("/timeline/{session_id}")
async def get_timeline(session_id: str):
    """Get the timeline for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    session = sessions[session_id]
    
    if session["timeline"] is None:
        raise HTTPException(status_code=400, detail="Timeline not generated yet. Run /ask first.")
    
    timeline = session["timeline"]
    
    return {
        "session_id": session_id,
        "timeline_text": timeline.timeline_text,
        "entry_count": len(timeline.entries),
        "video_duration": timeline.video_duration
    }


@app.get("/cache-stats/{session_id}")
async def get_cache_stats(session_id: str):
    """
    Get KV cache statistics for a session.
    
    Returns metrics about prefix caching efficiency:
    - prompt_tokens: Total tokens in the prompt
    - cached_tokens: Tokens retrieved from cache
    - cache_hit_ratio: Percentage of tokens cached
    - total_requests: Number of questions asked
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    session = sessions[session_id]
    
    # Track cache statistics (simplified)
    stats = session.get("cache_stats", {
        "prompt_tokens": 0,
        "cached_tokens": 0,
        "cache_hit_ratio": 0.0,
        "total_requests": 0
    })
    
    return {
        "session_id": session_id,
        **stats
    }


def run_server(host: str = "0.0.0.0", port: int = 8081):
    """Run the API server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
