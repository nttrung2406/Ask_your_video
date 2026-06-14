"""
Video Processor Module
Handles keyframe extraction using OpenCV
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional
from loguru import logger

from pipeline.interface.video_interfaces import ExtractedFrame


# Default FPS from environment
DEFAULT_TARGET_FPS = int(os.environ.get("TARGET_FPS", "5"))


class VideoProcessor:
    """
    Handles video processing operations including:
    - Keyframe extraction at specified FPS
    - Frame downsampling
    """
    
    def __init__(
        self,
        target_fps: int = None,  
        output_format: str = "jpg",
        quality: int = 95
    ):
        """
        Initialize VideoProcessor.
        
        Args:
            target_fps: Target frames per second for extraction (default: from TARGET_FPS env)
            output_format: Output image format (jpg, png)
            quality: JPEG quality (1-100)
        """
        self.target_fps = target_fps if target_fps is not None else DEFAULT_TARGET_FPS
        self.output_format = output_format
        self.quality = quality
        
    def extract_keyframes(
        self,
        video_path: str,
        output_dir: str,
        keep_in_memory: bool = False
    ) -> List[ExtractedFrame]:
        """
        Extract keyframes from video at target FPS.
        
        Args:
            video_path: Path to input video file
            output_dir: Directory to save extracted frames
            keep_in_memory: Whether to keep frame data in memory
            
        Returns:
            List of ExtractedFrame objects with metadata
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        logger.info(f"Extracting keyframes from: {video_path}")
        logger.info(f"Target FPS: {self.target_fps}")
        
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {video_path}")
        
        # Get video properties
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / original_fps if original_fps > 0 else 0
        
        logger.info(f"Video properties: {original_fps:.2f} FPS, {total_frames} frames, {duration:.2f}s duration")
        
        # Calculate frame interval for target FPS
        frame_interval = max(1, int(original_fps / self.target_fps))
        
        extracted_frames: List[ExtractedFrame] = []
        frame_count = 0
        extracted_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Extract frame at target interval
                if frame_count % frame_interval == 0:
                    timestamp = frame_count / original_fps
                    frame_filename = f"frame_{extracted_count:06d}.{self.output_format}"
                    frame_path = output_dir / frame_filename
                    
                    # Save frame
                    if self.output_format.lower() == "jpg":
                        cv2.imwrite(
                            str(frame_path),
                            frame,
                            [cv2.IMWRITE_JPEG_QUALITY, self.quality]
                        )
                    else:
                        cv2.imwrite(str(frame_path), frame)
                    
                    extracted_frame = ExtractedFrame(
                        frame_index=extracted_count,
                        timestamp=timestamp,
                        frame_path=str(frame_path),
                        frame_data=frame if keep_in_memory else None
                    )
                    extracted_frames.append(extracted_frame)
                    extracted_count += 1
                
                frame_count += 1
                
        finally:
            cap.release()
        
        logger.info(f"Extracted {extracted_count} keyframes from {frame_count} total frames")
        
        return extracted_frames
    
    def get_video_info(self, video_path: str) -> dict:
        """
        Get video metadata.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video properties
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {video_path}")
        
        try:
            info = {
                "fps": cap.get(cv2.CAP_PROP_FPS),
                "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "duration": cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
                    if cap.get(cv2.CAP_PROP_FPS) > 0 else 0
            }
            return info
        finally:
            cap.release()


def extract_keyframes(
    video_path: str,
    output_dir: str,
    target_fps: int = None,
    keep_in_memory: bool = False
) -> List[ExtractedFrame]:
    """
    Convenience function to extract keyframes from a video.
    
    Args:
        video_path: Path to input video
        output_dir: Directory to save frames
        target_fps: Target frames per second (default: from TARGET_FPS env)
        keep_in_memory: Whether to keep frame data in memory
        
    Returns:
        List of ExtractedFrame objects
    """
    fps = target_fps if target_fps is not None else DEFAULT_TARGET_FPS
    processor = VideoProcessor(target_fps=fps)
    return processor.extract_keyframes(video_path, output_dir, keep_in_memory)
