"""
Pipeline Package
Video Reasoning Pipeline - 4 Phases

Structure:
- interface/: All dataclasses and interfaces
- controller/: All controller/processor classes
"""

# Import interfaces
from pipeline.interface import (
    ExtractedFrame,
    TranscriptSegment,
    FrameCaption,
    ReasoningResult,
    PreprocessingResult,
    TranslationResult,
    TimelineEntry,
    AggregatedTimeline,
    VideoReasoningResult,
    PipelineConfig,
    PipelineResult
)

# Import controllers
from pipeline.controller import (
    PreprocessorController,
    TranslatorController,
    AggregatorController,
    ReasonerController,
    PipelineController
)

# Convenience aliases
Preprocessor = PreprocessorController
Translator = TranslatorController
Aggregator = AggregatorController
Reasoner = ReasonerController
VideoReasoningPipeline = PipelineController

# Convenience functions
from pipeline.controller.preprocessor_controller import preprocess_video
from pipeline.controller.translator_controller import translate_video_content
from pipeline.controller.aggregator_controller import aggregate_timeline
from pipeline.controller.reasoner_controller import reason_about_video
from pipeline.controller.pipeline_controller import create_pipeline


__all__ = [
    # Interfaces
    "ExtractedFrame",
    "TranscriptSegment",
    "FrameCaption",
    "ReasoningResult",
    "PreprocessingResult",
    "TranslationResult",
    "TimelineEntry",
    "AggregatedTimeline",
    "VideoReasoningResult",
    "PipelineConfig",
    "PipelineResult",
    # Controllers
    "PreprocessorController",
    "TranslatorController",
    "AggregatorController",
    "ReasonerController",
    "PipelineController",
    # Aliases (for backward compatibility)
    "Preprocessor",
    "Translator",
    "Aggregator",
    "Reasoner",
    "VideoReasoningPipeline",
    # Convenience functions
    "preprocess_video",
    "translate_video_content",
    "aggregate_timeline",
    "reason_about_video",
    "create_pipeline",
    "create_pipeline",
]
