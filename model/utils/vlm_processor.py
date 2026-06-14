"""
Vision Language Model (VLM) Processor Module
Handles frame captioning using Moondream2
"""

import os
import torch
from pathlib import Path
from typing import List, Optional, Callable
from PIL import Image
from loguru import logger

from pipeline.interface.vlm_interfaces import FrameCaption

# Lazy imports for transformers
_model = None
_processor = None


class VLMProcessor:
    """
    Handles Vision-Language Model processing using Moondream2.
    Generates captions for video frames.
    """
    
    def __init__(
        self,
        model_name: str = "vikhyatk/moondream2",
        revision: str = "2025-01-09",  # Pin to stable revision
        precision: str = "auto",  # "4bit", "8bit", "fp16", "fp32", or "auto"
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize VLM Processor.
        
        Args:
            model_name: HuggingFace model name
            revision: Model revision/commit to use
            precision: Model precision (4bit, 8bit, fp16, fp32, auto)
                       "auto" will use 4bit on GPU, fp32 on CPU
            device: Device to use (cuda, cpu, or auto)
            cache_dir: Directory to cache models
        """
        self.model_name = model_name
        self.revision = revision
        self.cache_dir = cache_dir or os.environ.get("MODEL_CACHE_DIR", "/app/models")
        
        # Determine device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # Auto-select precision based on device
        if precision == "auto":
            if self.device == "cuda":
                self.precision = "4bit"
            else:
                self.precision = "fp32"  # CPU doesn't support bitsandbytes quantization
        else:
            self.precision = precision
        
        # Warn if trying to use quantization on CPU
        if self.device == "cpu" and self.precision in ("4bit", "8bit"):
            logger.warning(f"Quantization ({self.precision}) requires GPU. Falling back to fp32.")
            self.precision = "fp32"
        
        self.model = None
        self.tokenizer = None
        
        logger.info(f"VLM Processor initialized with {self.precision} precision on {self.device}")
    
    def load_model(self):
        """Load the Moondream2 model with specified precision."""
        if self.model is not None:
            return
        
        logger.info(f"Loading VLM model: {self.model_name}")
        logger.info(f"Precision: {self.precision}, Device: {self.device}")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Configure quantization
            model_kwargs = {
                "trust_remote_code": True,
                "cache_dir": self.cache_dir,
                "revision": self.revision,
            }
            
            if self.precision == "4bit":
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                model_kwargs["quantization_config"] = quantization_config
                model_kwargs["torch_dtype"] = torch.float16
                
            elif self.precision == "8bit":
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True
                )
                model_kwargs["quantization_config"] = quantization_config
                
            elif self.precision == "fp16":
                model_kwargs["torch_dtype"] = torch.float16
            
            elif self.precision == "fp32":
                model_kwargs["torch_dtype"] = torch.float32
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **model_kwargs
            )
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                cache_dir=self.cache_dir,
                revision=self.revision
            )
            
            # Move to device if not using bitsandbytes quantization
            # (quantized models are automatically placed on GPU)
            if self.precision in ("fp16", "fp32") and self.device == "cuda":
                self.model = self.model.to(self.device)
            
            logger.info("VLM model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load VLM model: {e}")
            raise
    
    def caption_frame(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail."
    ) -> str:
        """
        Generate caption for a single frame.
        
        Args:
            image_path: Path to image file
            prompt: Prompt for the VLM
            
        Returns:
            Generated caption string
        """
        self.load_model()
        
        # Load image
        image = Image.open(image_path).convert("RGB")
        
        # Encode image with model's encoder
        enc_image = self.model.encode_image(image)
        
        # Generate caption
        caption = self.model.answer_question(enc_image, prompt, self.tokenizer)
        
        return caption.strip()
    
    def caption_frames(
        self,
        frame_paths: List[str],
        timestamps: List[float],
        prompt: str = "Describe what is happening in this video frame.",
        batch_size: int = 1,
        progress_callback: Optional[callable] = None
    ) -> List[FrameCaption]:
        """
        Generate captions for multiple frames.
        
        Args:
            frame_paths: List of paths to frame images
            timestamps: List of timestamps for each frame
            prompt: Prompt for the VLM
            batch_size: Number of frames to process at once
            progress_callback: Optional callback(current, total) for progress
            
        Returns:
            List of FrameCaption objects
        """
        self.load_model()
        
        captions = []
        total = len(frame_paths)
        
        logger.info(f"Captioning {total} frames...")
        
        for i, (frame_path, timestamp) in enumerate(zip(frame_paths, timestamps)):
            try:
                caption = self.caption_frame(frame_path, prompt)
                
                frame_caption = FrameCaption(
                    frame_index=i,
                    timestamp=timestamp,
                    frame_path=frame_path,
                    caption=caption
                )
                captions.append(frame_caption)
                
                if progress_callback:
                    progress_callback(i + 1, total)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Captioned {i + 1}/{total} frames")
                    
            except Exception as e:
                logger.error(f"Failed to caption frame {frame_path}: {e}")
                # Add placeholder caption
                captions.append(FrameCaption(
                    frame_index=i,
                    timestamp=timestamp,
                    frame_path=frame_path,
                    caption="[Unable to generate caption]"
                ))
        
        logger.info(f"Completed captioning {len(captions)} frames")
        return captions
    
    def caption_with_custom_prompt(
        self,
        image_path: str,
        user_prompt: str
    ) -> str:
        """
        Generate caption with a custom user-provided prompt.
        This allows integration with backend for custom queries.
        
        Args:
            image_path: Path to image file
            user_prompt: Custom prompt from user
            
        Returns:
            Generated response string
        """
        return self.caption_frame(image_path, user_prompt)
    
    def unload_model(self):
        """Unload model from memory."""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("VLM model unloaded")


def caption_frames_from_paths(
    frame_paths: List[str],
    timestamps: List[float],
    precision: str = "auto",
    prompt: str = "Describe what is happening in this video frame."
) -> List[FrameCaption]:
    """
    Convenience function to caption frames.
    
    Args:
        frame_paths: List of paths to frame images
        timestamps: List of timestamps for each frame
        precision: Model precision (auto, 4bit, 8bit, fp16, fp32)
        prompt: Prompt for captioning
        
    Returns:
        List of FrameCaption objects
    """
    processor = VLMProcessor(precision=precision)
    return processor.caption_frames(frame_paths, timestamps, prompt)
