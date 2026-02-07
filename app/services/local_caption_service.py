"""
Local Image Captioning Service using Vision-Language Models

This module provides image captioning using local models from HuggingFace.
The model runs on CPU and is optimized for low-resource environments.

Model: nlpconnect/vit-gpt2-image-captioning
- ViT (Vision Transformer) for image encoding
- GPT-2 for caption generation
- CPU-friendly and efficient
"""

import os
from typing import Optional
from PIL import Image
import torch
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
from dotenv import load_dotenv

load_dotenv()


class LocalCaptionService:
    """
    Singleton service for local image captioning.
    
    Features:
    - Lazy loading: Model loads only when first needed
    - CPU-only: Explicitly configured for CPU execution
    - Singleton: Model loads once and reused across requests
    - Error handling: Graceful degradation on failures
    """
    
    _instance: Optional['LocalCaptionService'] = None
    _model = None
    _processor = None
    _tokenizer = None
    _model_loaded = False
    
    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(LocalCaptionService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize service (model loads on first use)"""
        self.model_name = os.getenv("LOCAL_VISION_MODEL", "nlpconnect/vit-gpt2-image-captioning")
        self.cache_dir = os.getenv("MODEL_CACHE_DIR", "./model_cache")
        self.device = "cpu"  # Force CPU usage
        
    def _load_model(self):
        """
        Lazy load the model, processor, and tokenizer.
        Only loads once per application lifecycle.
        """
        if self._model_loaded:
            return
            
        try:
            print(f"🔄 Loading local vision model: {self.model_name}")
            print(f"   📁 Cache directory: {self.cache_dir}")
            print(f"   💻 Device: {self.device}")
            
            # Create cache directory if it doesn't exist
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Load model components
            self._model = VisionEncoderDecoderModel.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            self._processor = ViTImageProcessor.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            
            # Move model to CPU and set to evaluation mode
            self._model = self._model.to(self.device)
            self._model.eval()
            
            self._model_loaded = True
            print(f"✅ Local vision model loaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to load local vision model: {type(e).__name__} - {str(e)}")
            raise Exception(f"Local vision model initialization failed: {str(e)}")
    
    def generate_caption(self, image: Image.Image, max_length: int = 64, num_beams: int = 4) -> str:
        """
        Generate a caption for an image using the local model.
        
        Args:
            image: PIL Image object
            max_length: Maximum length of generated caption (default: 64 tokens)
            num_beams: Number of beams for beam search (higher = better quality but slower)
        
        Returns:
            Generated caption as string
            
        Raises:
            Exception: If caption generation fails
        """
        try:
            # Lazy load model on first use
            if not self._model_loaded:
                self._load_model()
            
            print(f"   🖼️ Image info: size={image.size}, mode={image.mode}")
            
            # Convert image to RGB if needed
            if image.mode != "RGB":
                print(f"   🔄 Converting image from {image.mode} to RGB...")
                image = image.convert("RGB")
            
            # Preprocess image
            pixel_values = self._processor(
                images=image,
                return_tensors="pt"
            ).pixel_values.to(self.device)
            
            print(f"   🤖 Generating caption (max_length={max_length}, num_beams={num_beams})...")
            
            # Generate caption with improved parameters
            with torch.no_grad():  # Disable gradient calculation for inference
                output_ids = self._model.generate(
                    pixel_values,
                    max_length=max_length,
                    min_length=10,  # Ensure minimum caption length
                    num_beams=num_beams,  # Beam search for better quality
                    early_stopping=True,
                    no_repeat_ngram_size=2,  # Prevent word repetition
                    length_penalty=1.0,  # Neutral length preference
                    repetition_penalty=1.5,  # Penalize repetitive phrases
                    do_sample=False  # Use greedy/beam search (deterministic)
                )
            
            # Decode caption
            caption = self._tokenizer.decode(output_ids[0], skip_special_tokens=True)
            caption = caption.strip()
            
            # Capitalize first letter if needed
            if caption and not caption[0].isupper():
                caption = caption[0].upper() + caption[1:]
            
            return caption
            
        except Exception as e:
            error_msg = f"Failed to generate caption: {type(e).__name__} - {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def is_loaded(self) -> bool:
        """Check if model is currently loaded"""
        return self._model_loaded
    
    def get_model_info(self) -> dict:
        """Get information about the current model configuration"""
        return {
            "model_name": self.model_name,
            "cache_dir": self.cache_dir,
            "device": self.device,
            "loaded": self._model_loaded
        }


# Singleton instance
_service_instance: Optional[LocalCaptionService] = None


def get_local_caption_service() -> LocalCaptionService:
    """
    Get the singleton instance of LocalCaptionService.
    
    Returns:
        LocalCaptionService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = LocalCaptionService()
    return _service_instance
