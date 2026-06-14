"""
Audio Processor Module
Handles audio extraction using ffmpeg and transcription using whisper.cpp
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional
from loguru import logger
import srt

from pipeline.interface.audio_interfaces import TranscriptSegment


class AudioProcessor:
    """
    Handles audio processing operations including:
    - Audio extraction from video using ffmpeg
    - Audio transcription using whisper.cpp
    """
    
    def __init__(
        self,
        whisper_model: str = "base",
        whisper_cpp_path: Optional[str] = None,
        sample_rate: int = 16000
    ):
        """
        Initialize AudioProcessor.
        
        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large)
            whisper_cpp_path: Path to whisper.cpp installation
            sample_rate: Audio sample rate for whisper (default: 16000)
        """
        self.whisper_model = whisper_model
        self.whisper_cpp_path = whisper_cpp_path or os.environ.get(
            "WHISPER_CPP_PATH", "/opt/whisper.cpp"
        )
        self.sample_rate = sample_rate
        
        # Find whisper.cpp binary (check multiple possible locations)
        self.whisper_binary = self._find_whisper_binary()
        
    def _find_whisper_binary(self) -> Optional[str]:
        """Find the whisper.cpp binary in possible locations."""
        possible_paths = [
            Path(self.whisper_cpp_path) / "build" / "bin" / "whisper-cli",  # New cmake build
            Path(self.whisper_cpp_path) / "build" / "bin" / "main",  # Alternative cmake build
            Path(self.whisper_cpp_path) / "main",  # Old make build
            Path(self.whisper_cpp_path) / "whisper",  # Alternative name
        ]
        
        for binary_path in possible_paths:
            if binary_path.exists():
                logger.info(f"Found whisper.cpp binary at: {binary_path}")
                return str(binary_path)
        
        logger.warning(f"whisper.cpp binary not found in {self.whisper_cpp_path}")
        logger.warning("Transcription may fail. Please ensure whisper.cpp is built.")
        return None
    
    def _verify_whisper_installation(self):
        """Verify whisper.cpp is properly installed."""
        if self.whisper_binary is None:
            logger.warning("whisper.cpp binary not found")
            logger.warning("Transcription may fail. Please ensure whisper.cpp is built.")
    
    def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        audio_format: str = "wav"
    ) -> str:
        """
        Extract audio from video using ffmpeg.
        
        Args:
            video_path: Path to input video file
            output_path: Path for output audio file (optional)
            audio_format: Output audio format (wav, mp3, etc.)
            
        Returns:
            Path to extracted audio file
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if output_path is None:
            output_path = video_path.with_suffix(f".{audio_format}")
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Extracting audio from: {video_path}")
        logger.info(f"Output: {output_path}")
        
        # ffmpeg command for audio extraction
        # -ar: sample rate (16kHz for whisper)
        # -ac: mono audio
        # -y: overwrite output
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # 16-bit PCM for wav
            "-ar", str(self.sample_rate),
            "-ac", "1",  # Mono
            "-y",  # Overwrite
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Audio extraction completed: {output_path}")
            return str(output_path)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg error: {e.stderr}")
            raise RuntimeError(f"Failed to extract audio: {e.stderr}")
    
    def transcribe(
        self,
        audio_path: str,
        output_srt_path: Optional[str] = None,
        language: str = "auto"
    ) -> List[TranscriptSegment]:
        """
        Transcribe audio using whisper.cpp.
        
        Args:
            audio_path: Path to audio file (WAV format, 16kHz mono)
            output_srt_path: Path for SRT output (optional)
            language: Language code or 'auto' for detection
            
        Returns:
            List of TranscriptSegment objects
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Check whisper binary
        if self.whisper_binary is None:
            raise RuntimeError(
                f"whisper.cpp binary not found in {self.whisper_cpp_path}. "
                "Please ensure whisper.cpp is built."
            )
        
        model_path = Path(self.whisper_cpp_path) / "models" / f"ggml-{self.whisper_model}.bin"
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Whisper model not found: {model_path}. "
                f"Please download using: cd {self.whisper_cpp_path}/models && ./download-ggml-model.sh {self.whisper_model}"
            )
        
        # Create temp file for SRT output if not specified
        if output_srt_path is None:
            output_srt_path = audio_path.with_suffix(".srt")
        else:
            output_srt_path = Path(output_srt_path)
        
        output_srt_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Transcribing audio: {audio_path}")
        logger.info(f"Using model: {self.whisper_model}")
        
        # Build whisper.cpp command
        cmd = [
            self.whisper_binary,
            "-m", str(model_path),
            "-f", str(audio_path),
            "-osrt",  # Output SRT format
            "-of", str(output_srt_path.with_suffix("")),  # Output file prefix (whisper adds .srt)
            "-pp",  # Print progress
            "-t", "4",  # Threads
        ]
        
        if language != "auto":
            cmd.extend(["-l", language])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.whisper_cpp_path
            )
            logger.debug(f"Whisper output: {result.stdout}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Whisper error: {e.stderr}")
            raise RuntimeError(f"Transcription failed: {e.stderr}")
        
        # Parse SRT file
        srt_file = output_srt_path.with_suffix(".srt")
        if not srt_file.exists():
            # Try with the exact path
            srt_file = Path(str(output_srt_path.with_suffix("")) + ".srt")
        
        segments = self._parse_srt(str(srt_file))
        logger.info(f"Transcribed {len(segments)} segments")
        
        return segments
    
    def _parse_srt(self, srt_path: str) -> List[TranscriptSegment]:
        """
        Parse SRT file into TranscriptSegment objects.
        
        Args:
            srt_path: Path to SRT file
            
        Returns:
            List of TranscriptSegment objects
        """
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            subtitles = list(srt.parse(content))
            
            segments = []
            for sub in subtitles:
                segment = TranscriptSegment(
                    start_time=sub.start.total_seconds(),
                    end_time=sub.end.total_seconds(),
                    text=sub.content.strip()
                )
                segments.append(segment)
            
            return segments
            
        except Exception as e:
            logger.warning(f"Failed to parse SRT with srt library: {e}")
            # Fallback to manual parsing
            return self._parse_srt_manual(srt_path)
    
    def _parse_srt_manual(self, srt_path: str) -> List[TranscriptSegment]:
        """
        Manual SRT parsing fallback.
        """
        segments = []
        
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by double newline (subtitle blocks)
        blocks = re.split(r'\n\n+', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # Parse timestamp line (format: 00:00:00,000 --> 00:00:00,000)
                timestamp_match = re.match(
                    r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})',
                    lines[1]
                )
                
                if timestamp_match:
                    start_str, end_str = timestamp_match.groups()
                    start_time = self._parse_timestamp(start_str)
                    end_time = self._parse_timestamp(end_str)
                    text = ' '.join(lines[2:]).strip()
                    
                    segments.append(TranscriptSegment(
                        start_time=start_time,
                        end_time=end_time,
                        text=text
                    ))
        
        return segments
    
    def _parse_timestamp(self, ts: str) -> float:
        """Parse SRT timestamp to seconds."""
        # Replace comma with period for parsing
        ts = ts.replace(',', '.')
        parts = ts.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds


def extract_and_transcribe(
    video_path: str,
    output_dir: str,
    whisper_model: str = "base"
) -> List[TranscriptSegment]:
    """
    Convenience function to extract audio and transcribe from video.
    
    Args:
        video_path: Path to input video
        output_dir: Directory for output files
        whisper_model: Whisper model size
        
    Returns:
        List of TranscriptSegment objects
    """
    processor = AudioProcessor(whisper_model=whisper_model)
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract audio
    audio_path = output_dir / "audio.wav"
    processor.extract_audio(video_path, str(audio_path))
    
    # Transcribe
    srt_path = output_dir / "transcript.srt"
    segments = processor.transcribe(str(audio_path), str(srt_path))
    
    return segments
