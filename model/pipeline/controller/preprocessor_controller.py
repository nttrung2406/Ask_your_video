"""
Preprocessor Controller - Phase 1
Handles video preprocessing: audio extraction and keyframe extraction
"""

import os
from pathlib import Path
from typing import Optional
from loguru import logger

from utils.video_processor import VideoProcessor
from utils.audio_processor import AudioProcessor
from pipeline.interface import PreprocessingResult, ExtractedFrame


# Default FPS from environment
DEFAULT_TARGET_FPS = int(os.environ.get("TARGET_FPS", "5"))


class PreprocessorController:
    """
    Phase 1: Video Pre-Processing Controller
    
    Handles:
    - Audio extraction using ffmpeg
    - Keyframe extraction at target FPS using OpenCV
    """
    
    def __init__(
        self,
        target_fps: int = None,
        output_base_dir: str = "/app/output",
        audio_sample_rate: int = 16000
    ):
        """
        Initialize PreprocessorController.
        
        Args:
            target_fps: Target frames per second for keyframe extraction (default: from TARGET_FPS env)
            output_base_dir: Base directory for output files
            audio_sample_rate: Sample rate for extracted audio (16kHz for Whisper)
        """
        self.target_fps = target_fps if target_fps is not None else DEFAULT_TARGET_FPS
        self.output_base_dir = Path(output_base_dir)
        self.audio_sample_rate = audio_sample_rate
        
        self.video_processor = VideoProcessor(target_fps=self.target_fps)
        self.audio_processor = AudioProcessor(sample_rate=audio_sample_rate)
        
    def process(
        self,
        video_path: str,
        session_id: Optional[str] = None
    ) -> PreprocessingResult:
        """
        Preprocess a video file.
        
        Args:
            video_path: Path to input video file
            session_id: Optional session identifier for output organization
            
        Returns:
            PreprocessingResult with extracted audio and frames
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        logger.info(f"Starting preprocessing for: {video_path}")
        
        # Create output directory
        if session_id:
            output_dir = self.output_base_dir / session_id
        else:
            output_dir = self.output_base_dir / video_path.stem
        
        output_dir.mkdir(parents=True, exist_ok=True)
        frames_dir = output_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        
        # Get video info
        video_info = self.video_processor.get_video_info(str(video_path))
        logger.info(f"Video info: {video_info}")
        
        # Phase 1a: Extract audio
        logger.info("Phase 1a: Extracting audio...")
        audio_path = output_dir / "audio.wav"
        self.audio_processor.extract_audio(str(video_path), str(audio_path))
        
        # Phase 1b: Extract keyframes
        logger.info(f"Phase 1b: Extracting keyframes at {self.target_fps} FPS...")
        frames = self.video_processor.extract_keyframes(
            str(video_path),
            str(frames_dir),
            keep_in_memory=False
        )
        
        result = PreprocessingResult(
            video_path=str(video_path),
            audio_path=str(audio_path),
            frames=frames,
            video_info=video_info,
            output_dir=str(output_dir)
        )
        
        logger.info(f"Preprocessing complete. Extracted {len(frames)} frames.")
        logger.info(f"Output directory: {output_dir}")
        
        return result


def preprocess_video(
    video_path: str,
    target_fps: int = None,
    output_dir: str = "/app/output"
) -> PreprocessingResult:
    """
    Convenience function to preprocess a video.
    
    Args:
        video_path: Path to video file
        target_fps: Target FPS for keyframe extraction (default: from TARGET_FPS env)
        output_dir: Output directory
        
    Returns:
        PreprocessingResult object
    """
    fps = target_fps if target_fps is not None else DEFAULT_TARGET_FPS
    controller = PreprocessorController(target_fps=fps, output_base_dir=output_dir)
    return controller.process(video_path)
