"""
Video Interfaces
Dataclasses for video processing
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class ExtractedFrame:
    """Represents an extracted keyframe with metadata."""
    frame_index: int
    timestamp: float  # in seconds
    frame_path: str
    frame_data: Optional[np.ndarray] = None
    
    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "timestamp": self.timestamp,
            "frame_path": self.frame_path
        }
