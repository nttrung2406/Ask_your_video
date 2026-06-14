"""
Pipeline Controller
Main orchestrator that combines all phases
"""

import os
import json
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from loguru import logger

from pipeline.interface import (
    PipelineConfig,
    PipelineResult,
    PreprocessingResult,
    TranslationResult,
    AggregatedTimeline,
    VideoReasoningResult
)
from pipeline.controller.preprocessor_controller import PreprocessorController
from pipeline.controller.translator_controller import TranslatorController
from pipeline.controller.aggregator_controller import AggregatorController
from pipeline.controller.reasoner_controller import ReasonerController


class PipelineController:
    """
    Main Video Reasoning Pipeline Controller
    
    Orchestrates all four phases:
    1. Preprocessing (audio + keyframe extraction)
    2. Translation (audio transcription + frame captioning)
    3. Aggregation (timeline structuring)
    4. Reasoning (LLM inference with DeepSeek)
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline controller.
        
        Args:
            config: Pipeline configuration (uses defaults if None)
        """
        self.config = config or PipelineConfig.from_env()
        
        # Initialize component controllers
        self.preprocessor = PreprocessorController(
            target_fps=self.config.target_fps,
            output_base_dir=self.config.output_base_dir,
            audio_sample_rate=self.config.audio_sample_rate
        )
        
        self.translator = TranslatorController(
            whisper_model=self.config.whisper_model,
            vlm_precision=self.config.vlm_precision,
            vlm_prompt=self.config.vlm_prompt
        )
        
        self.aggregator = AggregatorController(
            frame_group_threshold=self.config.frame_group_threshold,
            include_all_frames=self.config.include_all_frames
        )
        
        self.reasoner = ReasonerController(
            model_path=self.config.llm_model_path,
            context_size=self.config.llm_context_size,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens
        )
        
        logger.info("Pipeline Controller initialized")
        logger.debug(f"Config: {self.config.to_dict()}")
    
    def run(
        self,
        video_path: str,
        question: str,
        session_id: Optional[str] = None,
        custom_vlm_prompt: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> PipelineResult:
        """
        Run the complete video reasoning pipeline.
        
        Args:
            video_path: Path to input video file
            question: User question about the video
            session_id: Optional session identifier
            custom_vlm_prompt: Optional custom prompt for VLM
            progress_callback: Optional callback(phase, current, total)
            
        Returns:
            PipelineResult object
        """
        start_time = datetime.now()
        
        # Generate session ID if not provided
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info(f"Starting pipeline for session: {session_id}")
        logger.info(f"Video: {video_path}")
        logger.info(f"Question: {question}")
        
        try:
            # Phase 1: Preprocessing
            if progress_callback:
                progress_callback("preprocessing", 0, 1)
            
            preprocessing_result = self.preprocessor.process(video_path, session_id)
            
            if progress_callback:
                progress_callback("preprocessing", 1, 1)
            
            # Phase 2: Translation
            def translation_progress(current, total):
                if progress_callback:
                    progress_callback("translation", current, total)
            
            translation_result = self.translator.translate(
                preprocessing_result.audio_path,
                preprocessing_result.frames,
                preprocessing_result.output_dir,
                custom_vlm_prompt=custom_vlm_prompt,
                language=self.config.audio_language,
                progress_callback=translation_progress
            )
            
            # Phase 3: Aggregation
            if progress_callback:
                progress_callback("aggregation", 0, 1)
            
            timeline = self.aggregator.aggregate(
                translation_result.audio_segments,
                translation_result.frame_captions,
                preprocessing_result.video_info.get("duration")
            )
            
            if progress_callback:
                progress_callback("aggregation", 1, 1)
            
            # Phase 4: Reasoning
            if progress_callback:
                progress_callback("reasoning", 0, 1)
            
            reasoning_result = self.reasoner.reason(timeline, question)
            
            if progress_callback:
                progress_callback("reasoning", 1, 1)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Build result
            result = PipelineResult(
                session_id=session_id,
                video_path=video_path,
                question=question,
                answer=reasoning_result.answer,
                thinking_process=reasoning_result.thinking_process,
                timeline_text=timeline.timeline_text,
                processing_time=processing_time,
                preprocessing_result=preprocessing_result.to_dict(),
                translation_result=translation_result.to_dict(),
                aggregation_result=timeline.to_dict(),
                reasoning_result=reasoning_result.to_dict()
            )
            
            # Save results if configured
            if self.config.save_intermediate:
                self._save_results(result, preprocessing_result.output_dir)
            
            logger.info(f"Pipeline completed in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            raise
    
    def preprocess_only(
        self,
        video_path: str,
        session_id: Optional[str] = None
    ) -> PreprocessingResult:
        """
        Run only the preprocessing phase.
        Useful for preparing video before asking questions.
        
        Args:
            video_path: Path to video file
            session_id: Optional session ID
            
        Returns:
            PreprocessingResult object
        """
        return self.preprocessor.process(video_path, session_id)
    
    def translate_only(
        self,
        preprocessing_result: PreprocessingResult,
        custom_vlm_prompt: Optional[str] = None
    ) -> TranslationResult:
        """
        Run only the translation phase.
        
        Args:
            preprocessing_result: Result from preprocessing
            custom_vlm_prompt: Optional custom VLM prompt
            
        Returns:
            TranslationResult object
        """
        return self.translator.translate(
            preprocessing_result.audio_path,
            preprocessing_result.frames,
            preprocessing_result.output_dir,
            custom_vlm_prompt=custom_vlm_prompt,
            language=self.config.audio_language
        )
    
    def reason_only(
        self,
        timeline: AggregatedTimeline,
        question: str
    ) -> VideoReasoningResult:
        """
        Run only the reasoning phase.
        Useful for asking multiple questions about same video.
        
        Args:
            timeline: Aggregated timeline
            question: User question
            
        Returns:
            VideoReasoningResult object
        """
        return self.reasoner.reason(timeline, question)
    
    def _save_results(self, result: PipelineResult, output_dir: str):
        """Save pipeline results to files."""
        output_dir = Path(output_dir)
        
        # Save full result as JSON
        result_file = output_dir / "result.json"
        with open(result_file, 'w') as f:
            f.write(result.to_json())
        
        # Save timeline separately
        timeline_file = output_dir / "timeline.txt"
        with open(timeline_file, 'w') as f:
            f.write(result.timeline_text)
        
        # Save answer
        answer_file = output_dir / "answer.txt"
        with open(answer_file, 'w') as f:
            f.write(f"Question: {result.question}\n\n")
            f.write(f"Answer: {result.answer}\n")
            if result.thinking_process:
                f.write(f"\nThinking Process:\n{result.thinking_process}\n")
        
        logger.info(f"Results saved to {output_dir}")
    
    def cleanup(self):
        """Cleanup and unload models."""
        self.translator.unload_models()
        self.reasoner.unload_model()
        logger.info("Pipeline cleanup complete")


def create_pipeline(config: Optional[Dict[str, Any]] = None) -> PipelineController:
    """
    Factory function to create a pipeline controller.
    
    Args:
        config: Optional config dictionary
        
    Returns:
        PipelineController instance
    """
    if config:
        pipeline_config = PipelineConfig(**config)
    else:
        pipeline_config = PipelineConfig.from_env()
    
    return PipelineController(pipeline_config)
