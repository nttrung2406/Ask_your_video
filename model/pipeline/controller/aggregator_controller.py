"""
Aggregator Controller - Phase 3
Combines audio and visual outputs into a structured timeline prompt
"""

from typing import List, Optional
from loguru import logger

from pipeline.interface import (
    TranscriptSegment,
    FrameCaption,
    TimelineEntry,
    AggregatedTimeline
)


class AggregatorController:
    """
    Phase 3: Text Aggregation & Prompt Structuring Controller
    
    Combines audio transcripts and frame captions into
    a chronological timeline for the reasoning model.
    """
    
    def __init__(
        self,
        frame_group_threshold: float = 1.0,  # Group frames within this time window
        include_all_frames: bool = False  # Whether to include all frames or sample
    ):
        """
        Initialize AggregatorController.
        
        Args:
            frame_group_threshold: Time threshold for grouping similar frames
            include_all_frames: Whether to include all frames in timeline
        """
        self.frame_group_threshold = frame_group_threshold
        self.include_all_frames = include_all_frames
    
    def aggregate(
        self,
        audio_segments: List[TranscriptSegment],
        frame_captions: List[FrameCaption],
        video_duration: Optional[float] = None
    ) -> AggregatedTimeline:
        """
        Aggregate audio and visual data into a timeline.
        
        Args:
            audio_segments: List of audio transcript segments
            frame_captions: List of frame captions
            video_duration: Optional video duration in seconds
            
        Returns:
            AggregatedTimeline object
        """
        logger.info("Phase 3: Aggregating timeline...")
        
        entries: List[TimelineEntry] = []
        
        # Process frame captions
        if self.include_all_frames:
            visual_entries = self._process_all_frames(frame_captions)
        else:
            visual_entries = self._process_frames_grouped(frame_captions)
        
        entries.extend(visual_entries)
        
        # Process audio segments
        audio_entries = self._process_audio(audio_segments)
        entries.extend(audio_entries)
        
        # Sort by start time
        entries.sort(key=lambda x: x.start_time)
        
        # Calculate video duration if not provided
        if video_duration is None and entries:
            video_duration = max(e.end_time for e in entries)
        elif video_duration is None:
            video_duration = 0.0
        
        # Generate timeline text
        timeline_text = self._generate_timeline_text(entries)
        
        result = AggregatedTimeline(
            entries=entries,
            timeline_text=timeline_text,
            video_duration=video_duration
        )
        
        logger.info(f"Generated timeline with {len(entries)} entries")
        return result
    
    def _process_all_frames(
        self,
        frame_captions: List[FrameCaption]
    ) -> List[TimelineEntry]:
        """Process all frames into timeline entries."""
        entries = []
        
        for i, caption in enumerate(frame_captions):
            # Estimate end time (next frame or +1 second)
            if i < len(frame_captions) - 1:
                end_time = frame_captions[i + 1].timestamp
            else:
                end_time = caption.timestamp + 1.0
            
            entry = TimelineEntry(
                start_time=caption.timestamp,
                end_time=end_time,
                entry_type="visual",
                content=caption.caption
            )
            entries.append(entry)
        
        return entries
    
    def _process_frames_grouped(
        self,
        frame_captions: List[FrameCaption]
    ) -> List[TimelineEntry]:
        """
        Process frames with grouping to reduce redundancy.
        Groups similar consecutive captions.
        """
        if not frame_captions:
            return []
        
        entries = []
        current_group_start = frame_captions[0].timestamp
        current_group_captions = [frame_captions[0].caption]
        
        for i in range(1, len(frame_captions)):
            caption = frame_captions[i]
            prev_caption = frame_captions[i - 1]
            
            # Check if we should start a new group
            time_diff = caption.timestamp - prev_caption.timestamp
            
            if time_diff > self.frame_group_threshold or i == len(frame_captions) - 1:
                # Finalize current group
                if i == len(frame_captions) - 1:
                    current_group_captions.append(caption.caption)
                    end_time = caption.timestamp + 1.0
                else:
                    end_time = prev_caption.timestamp + 0.5
                
                # Use the most descriptive caption from the group
                best_caption = max(current_group_captions, key=len)
                
                entry = TimelineEntry(
                    start_time=current_group_start,
                    end_time=end_time,
                    entry_type="visual",
                    content=best_caption
                )
                entries.append(entry)
                
                # Start new group
                if i < len(frame_captions) - 1:
                    current_group_start = caption.timestamp
                    current_group_captions = [caption.caption]
            else:
                current_group_captions.append(caption.caption)
        
        return entries
    
    def _process_audio(
        self,
        audio_segments: List[TranscriptSegment]
    ) -> List[TimelineEntry]:
        """Process audio segments into timeline entries."""
        entries = []
        
        for segment in audio_segments:
            if segment.text.strip():  # Skip empty segments
                entry = TimelineEntry(
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    entry_type="audio",
                    content=segment.text
                )
                entries.append(entry)
        
        return entries
    
    def _generate_timeline_text(self, entries: List[TimelineEntry]) -> str:
        """Generate formatted timeline text."""
        lines = []
        for entry in entries:
            lines.append(entry.to_string())
        return "\n".join(lines)
    
    def build_reasoning_prompt(
        self,
        timeline: AggregatedTimeline,
        question: str,
        system_context: Optional[str] = None
    ) -> str:
        """
        Build the complete reasoning prompt.
        
        Args:
            timeline: Aggregated timeline
            question: User question
            system_context: Optional additional context
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # System context
        if system_context:
            prompt_parts.append(system_context)
        else:
            prompt_parts.append(
                "You are a video reasoning assistant. Below is a textual timeline "
                "representation of a short video. Analyze it carefully to answer the question."
            )
        
        prompt_parts.append("")
        
        # Video timeline
        prompt_parts.append("[VIDEO TIMELINE]")
        prompt_parts.append(timeline.timeline_text)
        prompt_parts.append("")
        
        # User question
        prompt_parts.append("[USER QUESTION]")
        prompt_parts.append(question)
        prompt_parts.append("")
        
        # Reasoning section
        prompt_parts.append("[REASONING COMPONENT]")
        prompt_parts.append("Let me analyze this video step by step:")
        prompt_parts.append("")
        prompt_parts.append("Thinking Process:")
        
        return "\n".join(prompt_parts)


def aggregate_timeline(
    audio_segments: List[TranscriptSegment],
    frame_captions: List[FrameCaption],
    video_duration: Optional[float] = None
) -> AggregatedTimeline:
    """
    Convenience function to aggregate timeline.
    
    Args:
        audio_segments: List of audio segments
        frame_captions: List of frame captions
        video_duration: Optional video duration
        
    Returns:
        AggregatedTimeline object
    """
    controller = AggregatorController()
    return controller.aggregate(audio_segments, frame_captions, video_duration)
