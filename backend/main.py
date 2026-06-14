import os
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Video Module 
from src.video_module.infrastructure.adapters.redis_cache import RedisCacheAdapter
from src.video_module.infrastructure.adapters.model_service import ModelServiceAdapter
from src.video_module.infrastructure.adapters.file_storage import LocalFileStorageAdapter


from src.video_module.application.services.video_service import VideoService

from src.video_module.infrastructure.controllers import video_controller

# Reasoning Module 
from src.reasoning_module.infrastructure.adapters.model_reasoning_adapter import (
    ModelServiceReasoningAdapter
)
from src.reasoning_module.infrastructure.adapters.video_session_adapter import (
    VideoSessionAdapter
)
from src.reasoning_module.infrastructure.adapters.reasoning_cache_adapter import (
    ReasoningCacheAdapter
)
from src.reasoning_module.application.services.reasoning_service import ReasoningService

from src.reasoning_module.infrastructure.controllers.reasoning_controller import (
    router as reasoning_router,
    set_reasoning_service
)


REDIS_URL = os.getenv("REDIS_URL", "redis://session-redis:6379")
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://video_reasoning_model:8081")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))

redis_adapter: Optional[RedisCacheAdapter] = None
model_adapter: Optional[ModelServiceAdapter] = None
reasoning_model_adapter: Optional[ModelServiceReasoningAdapter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    global redis_adapter, model_adapter, reasoning_model_adapter
    
    logger.info("Starting Video Reasoning Backend...")
    logger.info(f"Redis URL: {REDIS_URL}")
    logger.info(f"Model Service URL: {MODEL_SERVICE_URL}")
    logger.info(f"Upload Directory: {UPLOAD_DIR}")
    
    # Initialize Video Module adapters
    redis_adapter = RedisCacheAdapter(redis_url=REDIS_URL)
    model_adapter = ModelServiceAdapter(base_url=MODEL_SERVICE_URL)
    file_adapter = LocalFileStorageAdapter(base_path=UPLOAD_DIR)
    
    # Initialize Video Module service
    video_service = VideoService(
        cache_repository=redis_adapter,
        model_service=model_adapter,
        file_storage=file_adapter,
        cache_ttl_seconds=CACHE_TTL_HOURS * 3600,
    )
    
    # Initialize Reasoning Module adapters
    reasoning_model_adapter = ModelServiceReasoningAdapter(base_url=MODEL_SERVICE_URL)
    video_session_adapter = VideoSessionAdapter(video_service=video_service)
    
    await redis_adapter._get_client()
    reasoning_cache_adapter = ReasoningCacheAdapter(redis_client=redis_adapter.redis_client)
    
    # Initialize Reasoning Module service
    reasoning_service = ReasoningService(
        reasoning_service=reasoning_model_adapter,
        video_session=video_session_adapter,
        cache_repository=reasoning_cache_adapter,
        cache_ttl_seconds=CACHE_TTL_HOURS * 3600,
    )
    
    # Inject services into controllers
    video_controller.set_video_service(video_service)
    set_reasoning_service(reasoning_service)
    
    logger.info("Backend initialized successfully (Video + Reasoning modules)")
    
    yield
    
    # Cleanup
    logger.info("Shutting down...")
    if redis_adapter:
        await redis_adapter.close()
    if model_adapter:
        await model_adapter.close()
    if reasoning_model_adapter:
        await reasoning_model_adapter.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Video Reasoning Backend",
    description="Backend API for video upload, preprocessing, and Q&A",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(video_controller.router)
app.include_router(reasoning_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "video-reasoning-backend",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Simple health check."""
    return {"status": "healthy"}


@app.get("/docs", include_in_schema=False)
async def docs_redirect():
    """Redirect to OpenAPI docs."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
