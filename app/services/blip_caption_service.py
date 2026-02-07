"""
BLIP-based Image Captioning Service

Uses Salesforce BLIP model for high-quality image captions.
BLIP provides significantly better caption quality than ViT-GPT2.

Model: Salesforce/blip-image-captioning-base (or -large)
- Better object recognition
- More detailed descriptions
- Better text detection in images
- Less generic captions
"""

import os
from typing import Optional
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from dotenv import load_dotenv

load_dotenv()


class BlipCaptionService:
    """
    Singleton service for BLIP image captioning.
    
    Features:
    - Lazy loading: Model loads only when first needed
    - CPU-only: Explicitly configured for CPU execution
    - Singleton: Model loads once and reused across requests
    - High quality: Much better captions than ViT-GPT2
    """
    
    _instance: Optional['BlipCaptionService'] = None
    _model = None
    _processor = None
    _model_loaded = False
    
    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(BlipCaptionService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize service (model loads on first use)"""
        self.model_name = os.getenv("LOCAL_VISION_MODEL", "Salesforce/blip-image-captioning-base")
        self.cache_dir = os.getenv("MODEL_CACHE_DIR", "./model_cache")
        self.device = "cpu"  # Force CPU usage
        
    def _load_model(self):
        """
        Lazy load the BLIP model and processor.
        Only loads once per application lifecycle.
        """
        if self._model_loaded:
            return
            
        try:
            print(f"🔄 Loading BLIP vision model: {self.model_name}")
            print(f"   📁 Cache directory: {self.cache_dir}")
            print(f"   💻 Device: {self.device}")
            
            # Create cache directory if it doesn't exist
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Load BLIP processor and model
            self._processor = BlipProcessor.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            self._model = BlipForConditionalGeneration.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            
            # Move model to CPU and set to evaluation mode
            self._model = self._model.to(self.device)
            self._model.eval()
            
            self._model_loaded = True
            print(f"✅ BLIP model loaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to load BLIP model: {type(e).__name__} - {str(e)}")
            raise Exception(f"BLIP model initialization failed: {str(e)}")
    
    def generate_caption(self, image: Image.Image, max_length: int = 75, num_beams: int = 4) -> str:
        """
        Generate a caption for an image using BLIP model.
        
        Args:
            image: PIL Image object
            max_length: Maximum length of generated caption (default: 75 tokens)
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
            
            # Process image for BLIP
            inputs = self._processor(image, return_tensors="pt").to(self.device)
            
            print(f"   🤖 Generating caption with BLIP (max_length={max_length}, num_beams={num_beams})...")
            
            # Generate caption
            with torch.no_grad():  # Disable gradient calculation for inference
                output_ids = self._model.generate(
                    **inputs,
                    max_length=max_length,
                    min_length=10,
                    num_beams=num_beams,
                    early_stopping=True,
                    repetition_penalty=1.5,  # Prevent repetitive phrases
                    length_penalty=1.0,
                    no_repeat_ngram_size=2
                )
            
            # Decode caption
            caption = self._processor.decode(output_ids[0], skip_special_tokens=True)
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
            "loaded": self._model_loaded,
            "type": "BLIP",
            "quality": "High"
        }


# Singleton instance
_service_instance: Optional[BlipCaptionService] = None


def get_blip_caption_service() -> BlipCaptionService:
    """
    Get the singleton instance of BlipCaptionService.
    
    Returns:
        BlipCaptionService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = BlipCaptionService()
    return _service_instance
