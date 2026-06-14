
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

from src.reasoning_module.domain.models.reasoning import (
    ReasoningAnswer,
    CacheStats
)
from src.reasoning_module.domain.ports.reasoning_ports import ReasoningServicePort


class ModelServiceReasoningAdapter(ReasoningServicePort):
    """
    HTTP client adapter for the model service reasoning endpoint.
    
    Communicates with the model service which uses llama-server
    with KV cache optimization for efficient prefix caching.
    """
    
    def __init__(
        self,
        base_url: str = "http://video_reasoning_model:8081",
        timeout: float = 1200.0  # 20 minutes for reasoning
    ):
        """
        Initialize the adapter.
        
        Args:
            base_url: Base URL of the model service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout)
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def ask_question(
        self,
        session_id: str,
        question: str,
        vlm_prompt: Optional[str] = None
    ) -> ReasoningAnswer:
        """
        Ask a question about a preprocessed video.
        
        Uses the /ask endpoint which leverages KV cache for
        efficient prefix (timeline) caching.
        """
        client = await self._get_client()
        
        payload = {
            "session_id": session_id,
            "question": question
        }
        if vlm_prompt:
            payload["vlm_prompt"] = vlm_prompt
        
        logger.info(f"Sending question to model service: session={session_id}")
        
        # Retry logic for model service connection
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = await client.post("/ask", json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for cache hit indicator in response
                cache_hit = data.get("cache_hit", False)
                
                answer = ReasoningAnswer(
                    session_id=session_id,
                    question=question,
                    answer=data.get("answer", ""),
                    thinking_process=data.get("thinking_process"),
                    timeline_summary=data.get("timeline_summary"),
                    cache_hit=cache_hit,
                    created_at=datetime.utcnow()
                )
                
                logger.info(
                    f"Received answer from model service "
                    f"(cache_hit={cache_hit})"
                )
                
                return answer
                
            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    f"Model service connection failed "
                    f"(attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(5.0 * (attempt + 1))
                    continue
                raise ConnectionError(
                    f"Model service unavailable after {max_retries} attempts"
                )
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Model service error: {e.response.status_code} - "
                    f"{e.response.text}"
                )
                raise
        
        raise last_error or ConnectionError("Model service unavailable")
    
    async def get_timeline_text(self, session_id: str) -> Optional[str]:
        """Get the cached timeline text for a session."""
        client = await self._get_client()
        
        try:
            response = await client.get(f"/timeline/{session_id}")
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            data = response.json()
            
            return data.get("timeline_text")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get timeline: {e}")
            raise
        except Exception as e:
            logger.warning(f"Failed to get timeline text: {e}")
            return None
    
    async def get_cache_stats(self, session_id: str) -> CacheStats:
        """Get KV cache statistics for a session."""
        client = await self._get_client()
        
        try:
            response = await client.get(f"/cache-stats/{session_id}")
            
            if response.status_code == 404:
                return CacheStats()
            
            response.raise_for_status()
            data = response.json()
            
            return CacheStats(
                prompt_tokens=data.get("prompt_tokens", 0),
                cached_tokens=data.get("cached_tokens", 0),
                cache_hit_ratio=data.get("cache_hit_ratio", 0.0),
                total_requests=data.get("total_requests", 0)
            )
            
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return CacheStats()
    
    async def health_check(self) -> bool:
        """Check if the model service is healthy."""
        try:
            client = await self._get_client()
            response = await client.get("/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Model service health check failed: {e}")
            return False
