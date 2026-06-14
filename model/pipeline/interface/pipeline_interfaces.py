"""
Pipeline Interfaces
Dataclasses for the video reasoning pipeline
"""

import os
import json
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any

from pipeline.interface.video_interfaces import ExtractedFrame
from pipeline.interface.audio_interfaces import TranscriptSegment
from pipeline.interface.vlm_interfaces import FrameCaption


@dataclass
class PreprocessingResult:
    """Result from video preprocessing."""
    video_path: str
    audio_path: str
    frames: List[ExtractedFrame]
    video_info: dict
    output_dir: str
    
    def to_dict(self) -> dict:
        return {
            "video_path": self.video_path,
            "audio_path": self.audio_path,
            "frame_count": len(self.frames),
            "video_info": self.video_info,
            "output_dir": self.output_dir
        }


@dataclass
class TranslationResult:
    """Result from audio/visual translation."""
    audio_segments: List[TranscriptSegment]
    frame_captions: List[FrameCaption]
    
    def to_dict(self) -> dict:
        return {
            "audio_segments": [s.to_dict() for s in self.audio_segments],
            "frame_captions": [c.to_dict() for c in self.frame_captions]
        }


@dataclass
class TimelineEntry:
    """A single entry in the video timeline."""
    start_time: float
    end_time: float
    entry_type: str  # "visual" or "audio"
    content: str
    
    def format_timestamp(self, time_seconds: float) -> str:
        """Format timestamp as MM:SS."""
        minutes = int(time_seconds // 60)
        seconds = int(time_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def to_string(self) -> str:
        """Format entry as timeline string."""
        start_str = self.format_timestamp(self.start_time)
        end_str = self.format_timestamp(self.end_time)
        
        if self.entry_type == "visual":
            return f"{start_str} - {end_str} | Visual: {self.content}"
        else:
            return f"{start_str} - {end_str} | Audio Track (Subtitles): \"{self.content}\""


@dataclass 
class AggregatedTimeline:
    """Complete aggregated timeline for reasoning."""
    entries: List[TimelineEntry]
    timeline_text: str
    video_duration: float
    
    def to_dict(self) -> dict:
        return {
            "entry_count": len(self.entries),
            "video_duration": self.video_duration,
            "timeline_text": self.timeline_text
        }


@dataclass
class VideoReasoningResult:
    """Complete result from video reasoning."""
    question: str
    answer: str
    thinking_process: Optional[str]
    timeline_summary: str
    confidence: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "thinking_process": self.thinking_process,
            "timeline_summary": self.timeline_summary,
            "confidence": self.confidence
        }


@dataclass
class PipelineConfig:
    """Configuration for the video reasoning pipeline."""
    # Phase 1: Preprocessing - loaded from TARGET_FPS env var
    target_fps: int = field(default_factory=lambda: int(os.environ.get("TARGET_FPS")))
    audio_sample_rate: int = 16000
    
    # Phase 2: Translation
    whisper_model: str = "base"
    vlm_precision: str = "4bit"
    vlm_prompt: str = "Describe what is happening in this video frame in one or two sentences."
    audio_language: str = "auto"
    
    # Phase 3: Aggregation
    frame_group_threshold: float = 1.0
    include_all_frames: bool = False
    
    # Phase 4: Reasoning - DeepSeek model only
    llm_model_path: str = "/app/model_resource/DeepSeek-R1-Distill-Qwen-7B-Q3_K_M.gguf"
    llm_context_size: int = 4096
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    
    # General
    output_base_dir: str = "/app/output"
    save_intermediate: bool = True
    
    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Create config from environment variables."""
        return cls(
            target_fps=int(os.environ.get("TARGET_FPS", 5)),  # Default 5 FPS
            whisper_model=os.environ.get("WHISPER_MODEL", "base"),
            vlm_precision=os.environ.get("MOONDREAM_PRECISION", "4bit"),
            llm_model_path=os.environ.get(
                "LLAMA_MODEL_PATH",
                "/app/model_resource/DeepSeek-R1-Distill-Qwen-7B-Q3_K_M.gguf"
            ),
            output_base_dir=os.environ.get("OUTPUT_DIR", "/app/output")
        )
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelineResult:
    """Complete result from the video reasoning pipeline."""
    session_id: str
    video_path: str
    question: str
    answer: str
    thinking_process: Optional[str]
    timeline_text: str
    processing_time: float
    preprocessing_result: Dict[str, Any]
    translation_result: Dict[str, Any]
    aggregation_result: Dict[str, Any]
    reasoning_result: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "video_path": self.video_path,
            "question": self.question,
            "answer": self.answer,
            "thinking_process": self.thinking_process,
            "timeline_text": self.timeline_text,
            "processing_time": self.processing_time,
            "preprocessing": self.preprocessing_result,
            "translation": self.translation_result,
            "aggregation": self.aggregation_result,
            "reasoning": self.reasoning_result
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
