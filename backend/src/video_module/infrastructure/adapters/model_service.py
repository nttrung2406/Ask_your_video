import httpx
from typing import Optional, Dict, Any
from loguru import logger

from src.video_module.domain.models.video import PreprocessingResult
from src.video_module.domain.ports.video_ports import ModelServicePort


class ModelServiceAdapter(ModelServicePort):
    """HTTP client adapter for the model service."""
    
    def __init__(
        self,
        base_url: str = "http://video_reasoning_model:8081",
        timeout: float = 1200.0,  
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def upload_video(self, file_path: str, session_id: str) -> Dict[str, Any]:
        """Upload a video file to the model service."""
        client = await self._get_client()
        
        with open(file_path, "rb") as f:
            files = {"file": (file_path.split("/")[-1], f, "video/mp4")}
            data = {"session_id": session_id}
            
            response = await client.post("/upload", files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Video uploaded to model service: {result}")
            return result
    
    async def preprocess_video(self, video_path: str, session_id: str, vlm_prompt: Optional[str] = None) -> PreprocessingResult:
        """Preprocess a video using the model service."""
        client = await self._get_client()

        model_video_path = video_path.replace("/app/uploads/", "/app/data/uploads/")
        
        payload = {
            "video_path": model_video_path,
            "session_id": session_id,
        }
        
        if vlm_prompt:
            payload["vlm_prompt"] = vlm_prompt
        
        logger.info(f"Sending preprocess request to model service: {payload}")
        
        # Retry logic for model service connection
        max_retries = 5
        retry_delay = 5.0
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = await client.post("/preprocess", json=payload)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Preprocessing result: {data}")
                
                return PreprocessingResult(
                    audio_path=data["audio_path"],
                    frame_count=data["frame_count"],
                    video_info=data["video_info"],
                    output_dir=data["output_dir"],
                )
            except httpx.ConnectError as e:
                last_error = e
                logger.warning(f"Model service connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                raise ConnectionError(f"Model service unavailable after {max_retries} attempts. Please ensure the model service is running.")
            except httpx.HTTPStatusError as e:
                logger.error(f"Model service returned error: {e.response.status_code} - {e.response.text}")
                raise
        
        raise last_error or ConnectionError("Model service unavailable")
    
    async def ask_question(
        self,
        session_id: str,
        question: str,
    ) -> Dict[str, Any]:
        """Ask a question about a preprocessed video."""
        client = await self._get_client()
        
        payload = {
            "session_id": session_id,
            "question": question,
        }
        
        response = await client.post("/ask", json=payload)
        response.raise_for_status()
        
        return response.json()
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information from model service."""
        client = await self._get_client()
        
        try:
            response = await client.get(f"/session/{session_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def health_check(self) -> bool:
        """Check if model service is healthy."""
        try:
            client = await self._get_client()
            response = await client.get("/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Model service health check failed: {e}")
            return False
