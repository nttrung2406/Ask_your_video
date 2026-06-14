import argparse
import os
import sys
from pathlib import Path
from loguru import logger

from pipeline.controller.pipeline_controller import PipelineController
from pipeline.interface import PipelineConfig
from model_resource.config import DEEPSEEK_MODEL_PATH


def setup_logging(level: str = "INFO"):
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Video Reasoning Pipeline - Multimodal Video Analysis with DeepSeek"
    )
    
    parser.add_argument(
        "video",
        type=str,
        help="Path to input video file"
    )
    
    parser.add_argument(
        "question",
        type=str,
        help="Question about the video"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/app/output",
        help="Output directory for results"
    )
    
    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Session identifier"
    )
    
    parser.add_argument(
        "--fps",
        type=int,
        default=int(os.environ.get("TARGET_FPS", "5")),
        help="Target FPS for keyframe extraction (default: from TARGET_FPS env or 5)"
    )
    
    parser.add_argument(
        "--whisper-model",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size"
    )
    
    parser.add_argument(
        "--vlm-precision",
        type=str,
        default="4bit",
        choices=["4bit", "8bit", "fp16"],
        help="VLM precision"
    )
    
    parser.add_argument(
        "--vlm-prompt",
        type=str,
        default=None,
        help="Custom prompt for VLM captioning"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Validate video path
    video_path = Path(args.video)
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        sys.exit(1)
    
    # Create pipeline config (uses DeepSeek model by default)
    config = PipelineConfig(
        target_fps=args.fps,
        whisper_model=args.whisper_model,
        vlm_precision=args.vlm_precision,
        llm_model_path=DEEPSEEK_MODEL_PATH,
        output_base_dir=args.output_dir
    )
    
    if args.vlm_prompt:
        config.vlm_prompt = args.vlm_prompt
    
    # Create and run pipeline
    logger.info("=" * 60)
    logger.info("Video Reasoning Pipeline (DeepSeek)")
    logger.info("=" * 60)
    
    pipeline = PipelineController(config)
    
    def progress_callback(phase: str, current: int, total: int):
        logger.info(f"[{phase.upper()}] Progress: {current}/{total}")
    
    try:
        result = pipeline.run(
            video_path=str(video_path),
            question=args.question,
            session_id=args.session_id,
            custom_vlm_prompt=args.vlm_prompt,
            progress_callback=progress_callback
        )
        
        # Print results
        logger.info("=" * 60)
        logger.info("RESULTS")
        logger.info("=" * 60)
        
        print("\n" + "=" * 60)
        print("VIDEO TIMELINE")
        print("=" * 60)
        print(result.timeline_text)
        
        print("\n" + "=" * 60)
        print("QUESTION")
        print("=" * 60)
        print(result.question)
        
        print("\n" + "=" * 60)
        print("ANSWER")
        print("=" * 60)
        print(result.answer)
        
        if result.thinking_process:
            print("\n" + "=" * 60)
            print("THINKING PROCESS")
            print("=" * 60)
            print(result.thinking_process)
        
        print(f"\nProcessing time: {result.processing_time:.2f}s")
        print(f"Results saved to: {result.preprocessing_result['output_dir']}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
    finally:
        pipeline.cleanup()


if __name__ == "__main__":
    main()
