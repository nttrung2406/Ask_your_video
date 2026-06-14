"""
Reasoning HTTP Controller (API endpoints)
Handles video Q&A requests with KV cache optimization.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from src.reasoning_module.application.services.reasoning_service import ReasoningService


router = APIRouter(prefix="/api/reasoning", tags=["reasoning"])

reasoning_service: Optional[ReasoningService] = None


def set_reasoning_service(service: ReasoningService):
    """Set the reasoning service instance (called from main.py)."""
    global reasoning_service
    reasoning_service = service


# Request/Response Models
class AskQuestionRequest(BaseModel):
    """Request to ask a question about a video."""
    question: str = Field(..., description="The question to ask about the video")
    vlm_prompt: Optional[str] = Field(None, description="Optional custom VLM prompt")


class AskQuestionResponse(BaseModel):
    """Response to a question."""
    session_id: str
    question: str
    answer: str
    thinking_process: Optional[str] = None
    timeline_summary: Optional[str] = None
    processing_time: Optional[float] = None
    cache_hit: bool = False


class SessionStatusResponse(BaseModel):
    """Reasoning session status response."""
    session_id: str
    status: str
    is_timeline_cached: bool
    error_message: Optional[str] = None


class CacheStatsResponse(BaseModel):
    """KV cache statistics response."""
    session_id: str
    prompt_tokens: int
    cached_tokens: int
    cache_hit_ratio: float
    total_requests: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_service: str


# Endpoints
@router.post("/ask/{session_id}", response_model=AskQuestionResponse)
async def ask_question(session_id: str, request: AskQuestionRequest):
    """
    Ask a question about a preprocessed video.
    
    This endpoint uses KV cache optimization:
    - The video timeline is cached as a prefix
    - Subsequent questions reuse the cached KV computations
    - Monitor cache hits via the cache_hit field in response
    
    Args:
        session_id: The video session ID from preprocessing
        request: The question and optional VLM prompt
        
    Returns:
        AskQuestionResponse with the answer and metadata
    """
    if reasoning_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        answer = await reasoning_service.ask_question(
            session_id=session_id,
            question=request.question,
            vlm_prompt=request.vlm_prompt
        )
        
        return AskQuestionResponse(
            session_id=session_id,
            question=answer.question,
            answer=answer.answer,
            thinking_process=answer.thinking_process,
            timeline_summary=answer.timeline_summary,
            processing_time=answer.processing_time,
            cache_hit=answer.cache_hit
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Question error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """Get the reasoning session status."""
    if reasoning_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    session = await reasoning_service.get_session(session_id)
    
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Reasoning session not found: {session_id}"
        )
    
    return SessionStatusResponse(
        session_id=session.id,
        status=session.status.value,
        is_timeline_cached=session.is_timeline_cached,
        error_message=session.error_message
    )


@router.get("/timeline/{session_id}")
async def get_timeline_text(session_id: str):
    """Get the cached timeline text for a session."""
    if reasoning_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    timeline_text = await reasoning_service.get_timeline_text(session_id)
    
    if timeline_text is None:
        raise HTTPException(
            status_code=404,
            detail=f"Timeline not found for session: {session_id}"
        )
    
    return {
        "session_id": session_id,
        "timeline_text": timeline_text
    }


@router.get("/cache-stats/{session_id}", response_model=CacheStatsResponse)
async def get_cache_stats(session_id: str):
    """
    Get KV cache statistics for a session.
    
    Useful for monitoring cache efficiency:
    - prompt_tokens: Total tokens in the prompt
    - cached_tokens: Tokens retrieved from cache
    - cache_hit_ratio: Ratio of cached to total tokens
    - total_requests: Number of questions asked
    """
    if reasoning_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    stats = await reasoning_service.get_cache_stats(session_id)
    
    return CacheStatsResponse(
        session_id=session_id,
        prompt_tokens=stats.prompt_tokens,
        cached_tokens=stats.cached_tokens,
        cache_hit_ratio=stats.cache_hit_ratio,
        total_requests=stats.total_requests
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check for the reasoning service."""
    if reasoning_service is None:
        return HealthResponse(
            status="unhealthy",
            model_service="unknown"
        )
    
    health = await reasoning_service.health_check()
    return HealthResponse(**health)
