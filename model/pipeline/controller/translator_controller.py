"""
Translator Controller - Phase 2
Converts raw audio and visual data into text
"""

from pathlib import Path
from typing import List, Optional, Callable
from loguru import logger

from utils.audio_processor import AudioProcessor
from utils.vlm_processor import VLMProcessor
from pipeline.interface import (
    ExtractedFrame,
    TranscriptSegment,
    FrameCaption,
    TranslationResult
)


class TranslatorController:
    """
    Phase 2: Local Translation Controller
    
    Converts:
    - Audio to text using Whisper.cpp
    - Frames to text using Moondream2 VLM
    """
    
    def __init__(
        self,
        whisper_model: str = "base",
        vlm_precision: str = "auto",
        vlm_prompt: str = "Describe what is happening in this video frame in one or two sentences."
    ):
        """
        Initialize TranslatorController.
        
        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large)
            vlm_precision: VLM precision (auto, 4bit, 8bit, fp16, fp32)
            vlm_prompt: Default prompt for frame captioning
        """
        self.whisper_model = whisper_model
        self.vlm_precision = vlm_precision
        self.vlm_prompt = vlm_prompt
        
        self.audio_processor = AudioProcessor(whisper_model=whisper_model)
        self.vlm_processor = VLMProcessor(precision=vlm_precision)
        
    def translate_audio(
        self,
        audio_path: str,
        output_dir: str,
        language: str = "auto"
    ) -> List[TranscriptSegment]:
        """
        Transcribe audio to text.
        
        Args:
            audio_path: Path to audio file
            output_dir: Directory for output files
            language: Language code or 'auto'
            
        Returns:
            List of TranscriptSegment objects
        """
        logger.info("Phase 2a: Transcribing audio...")
        
        srt_path = Path(output_dir) / "transcript.srt"
        segments = self.audio_processor.transcribe(
            audio_path,
            str(srt_path),
            language
        )
        
        logger.info(f"Transcribed {len(segments)} audio segments")
        return segments
    
    def translate_frames(
        self,
        frames: List[ExtractedFrame],
        custom_prompt: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[FrameCaption]:
        """
        Generate captions for frames.
        
        Args:
            frames: List of ExtractedFrame objects
            custom_prompt: Optional custom prompt (for user queries)
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of FrameCaption objects
        """
        logger.info("Phase 2b: Captioning frames...")
        
        prompt = custom_prompt or self.vlm_prompt
        
        frame_paths = [f.frame_path for f in frames]
        timestamps = [f.timestamp for f in frames]
        
        captions = self.vlm_processor.caption_frames(
            frame_paths,
            timestamps,
            prompt=prompt,
            progress_callback=progress_callback
        )
        
        logger.info(f"Generated {len(captions)} frame captions")
        return captions
    
    def translate(
        self,
        audio_path: str,
        frames: List[ExtractedFrame],
        output_dir: str,
        custom_vlm_prompt: Optional[str] = None,
        language: str = "auto",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> TranslationResult:
        """
        Perform full translation of audio and visual data.
        
        Args:
            audio_path: Path to audio file
            frames: List of extracted frames
            output_dir: Output directory
            custom_vlm_prompt: Optional custom prompt for VLM
            language: Audio language code
            progress_callback: Optional progress callback
            
        Returns:
            TranslationResult object
        """
        logger.info("Starting Phase 2: Translation...")
        
        # Translate audio
        audio_segments = self.translate_audio(audio_path, output_dir, language)
        
        # Translate frames
        frame_captions = self.translate_frames(
            frames,
            custom_prompt=custom_vlm_prompt,
            progress_callback=progress_callback
        )
        
        result = TranslationResult(
            audio_segments=audio_segments,
            frame_captions=frame_captions
        )
        
        logger.info("Phase 2 complete")
        return result
    
    def unload_models(self):
        """Unload models from memory."""
        self.vlm_processor.unload_model()


def translate_video_content(
    audio_path: str,
    frames: List[ExtractedFrame],
    output_dir: str,
    whisper_model: str = "base",
    vlm_precision: str = "4bit"
) -> TranslationResult:
    """
    Convenience function for video content translation.
    
    Args:
        audio_path: Path to audio file
        frames: List of extracted frames
        output_dir: Output directory
        whisper_model: Whisper model size
        vlm_precision: VLM precision
        
    Returns:
        TranslationResult object
    """
    controller = TranslatorController(
        whisper_model=whisper_model,
        vlm_precision=vlm_precision
    )
    return controller.translate(audio_path, frames, output_dir)
