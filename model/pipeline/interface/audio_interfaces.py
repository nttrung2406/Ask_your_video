"""
Audio Interfaces
Dataclasses for audio processing
"""

from dataclasses import dataclass


@dataclass
class TranscriptSegment:
    """Represents a transcription segment with timestamps."""
    start_time: float  # in seconds
    end_time: float    # in seconds
    text: str
    
    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text
        }
