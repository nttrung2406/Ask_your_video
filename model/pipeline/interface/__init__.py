"""
Interface Package
Contains all dataclasses/interfaces for the video reasoning pipeline
"""

from pipeline.interface.video_interfaces import ExtractedFrame
from pipeline.interface.audio_interfaces import TranscriptSegment
from pipeline.interface.vlm_interfaces import FrameCaption
from pipeline.interface.llm_interfaces import ReasoningResult
from pipeline.interface.pipeline_interfaces import (
    PreprocessingResult,
    TranslationResult,
    TimelineEntry,
    AggregatedTimeline,
    VideoReasoningResult,
    PipelineConfig,
    PipelineResult
)


__all__ = [
    # Video
    "ExtractedFrame",
    # Audio
    "TranscriptSegment",
    # VLM
    "FrameCaption",
    # LLM
    "ReasoningResult",
    # Pipeline
    "PreprocessingResult",
    "TranslationResult",
    "TimelineEntry",
    "AggregatedTimeline",
    "VideoReasoningResult",
    "PipelineConfig",
    "PipelineResult",
]
