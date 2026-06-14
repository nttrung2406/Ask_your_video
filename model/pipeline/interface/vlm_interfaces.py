"""
VLM Interfaces
Dataclasses for Vision Language Model processing
"""

from dataclasses import dataclass


@dataclass
class FrameCaption:
    """Represents a frame with its generated caption."""
    frame_index: int
    timestamp: float  # in seconds
    frame_path: str
    caption: str
    
    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "timestamp": self.timestamp,
            "frame_path": self.frame_path,
            "caption": self.caption
        }
