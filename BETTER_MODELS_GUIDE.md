# Better Vision Models Guide

## ⚠️ Current Issue: Generic Captions

The `nlpconnect/vit-gpt2-image-captioning` model generates generic captions because:
1. It's a relatively small, simple model (~500MB)
2. Limited training data
3. Tends to produce repetitive descriptions

---

## 🚀 Recommended Alternative Models

### Option 1: BLIP (Salesforce) - **RECOMMENDED**

**Best balance of quality and speed for CPU**

```env
LOCAL_VISION_MODEL=Salesforce/blip-image-captioning-base
```

**Pros:**
- ✅ Much better caption quality
- ✅ More detailed and accurate descriptions
- ✅ CPU-friendly (~990MB)
- ✅ Trained on large datasets (COCO, Visual Genome)
- ✅ Better at detecting text in images

**Performance:**
- Model size: ~990MB
- CPU inference: 3-4 seconds per image
- Quality: ⭐⭐⭐⭐⭐ (Excellent)

**Sample Output:**
```
Input: netflix_creds.jpg
Current: "A computer screen with a picture of a person on it"
BLIP:    "Netflix login page showing username field 'hamza@example.com' and password field on laptop screen"
```

---

### Option 2: BLIP-Large (Better Quality, Slower)

```env
LOCAL_VISION_MODEL=Salesforce/blip-image-captioning-large
```

**Pros:**
- ✅ Highest quality captions
- ✅ More nuanced understanding

**Cons:**
- ❌ Larger model (~1.9GB)
- ❌ Slower on CPU (~5-6 seconds per image)

---

### Option 3: GIT (Microsoft) - Good Alternative

```env
LOCAL_VISION_MODEL=microsoft/git-base
```

**Pros:**
- ✅ Good caption quality
- ✅ Fast inference
- ✅ Trained on diverse datasets

**Performance:**
- Model size: ~700MB
- CPU inference: 2-3 seconds per image
- Quality: ⭐⭐⭐⭐ (Very Good)

---

## 🔧 How to Switch Models

### Step 1: Update Your Code

The current `LocalCaptionService` is designed for ViT-GPT2. BLIP uses a different architecture.

**Create a new file:** `app/services/blip_caption_service.py`

```python
"""
BLIP-based Image Captioning Service
Uses Salesforce BLIP model for high-quality captions
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
    BLIP provides much better caption quality than ViT-GPT2.
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
        self.device = "cpu"
        
    def _load_model(self):
        """Lazy load the BLIP model and processor"""
        if self._model_loaded:
            return
            
        try:
            print(f"🔄 Loading BLIP vision model: {self.model_name}")
            print(f"   📁 Cache directory: {self.cache_dir}")
            print(f"   💻 Device: {self.device}")
            
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
            
            # Move to CPU and set evaluation mode
            self._model = self._model.to(self.device)
            self._model.eval()
            
            self._model_loaded = True
            print(f"✅ BLIP model loaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to load BLIP model: {type(e).__name__} - {str(e)}")
            raise Exception(f"BLIP model initialization failed: {str(e)}")
    
    def generate_caption(self, image: Image.Image, max_length: int = 75) -> str:
        """
        Generate a caption using BLIP model.
        
        Args:
            image: PIL Image object
            max_length: Maximum caption length
        
        Returns:
            Generated caption as string
        """
        try:
            if not self._model_loaded:
                self._load_model()
            
            print(f"   🖼️ Image info: size={image.size}, mode={image.mode}")
            
            # Convert to RGB if needed
            if image.mode != "RGB":
                print(f"   🔄 Converting from {image.mode} to RGB...")
                image = image.convert("RGB")
            
            # Process image
            inputs = self._processor(image, return_tensors="pt").to(self.device)
            
            print(f"   🤖 Generating caption with BLIP (max_length={max_length})...")
            
            # Generate caption
            with torch.no_grad():
                output_ids = self._model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=4,
                    early_stopping=True,
                    repetition_penalty=1.5
                )
            
            # Decode caption
            caption = self._processor.decode(output_ids[0], skip_special_tokens=True)
            caption = caption.strip()
            
            # Capitalize first letter
            if caption and not caption[0].isupper():
                caption = caption[0].upper() + caption[1:]
            
            return caption
            
        except Exception as e:
            error_msg = f"Failed to generate caption: {type(e).__name__} - {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model_loaded
    
    def get_model_info(self) -> dict:
        """Get model configuration info"""
        return {
            "model_name": self.model_name,
            "cache_dir": self.cache_dir,
            "device": self.device,
            "loaded": self._model_loaded,
            "type": "BLIP"
        }


# Singleton instance
_service_instance: Optional[BlipCaptionService] = None


def get_blip_caption_service() -> BlipCaptionService:
    """Get the singleton instance of BlipCaptionService"""
    global _service_instance
    if _service_instance is None:
        _service_instance = BlipCaptionService()
    return _service_instance
```

### Step 2: Update Activity File

Modify `GoogleDriveImageRAGActivity.py`:

```python
# At the top, add:
from app.services.blip_caption_service import get_blip_caption_service

# In the processing loop, replace:
local_service = get_local_caption_service()

# With:
model_type = os.getenv("LOCAL_VISION_MODEL", "").lower()
if "blip" in model_type:
    local_service = get_blip_caption_service()
else:
    local_service = get_local_caption_service()
```

### Step 3: Update .env

```env
USE_LOCAL_VISION_MODEL=true
LOCAL_VISION_MODEL=Salesforce/blip-image-captioning-base
MODEL_CACHE_DIR=./model_cache
```

### Step 4: Install (if needed)

BLIP uses the same dependencies (torch, transformers, accelerate), so no new installations needed!

---

## 📊 Model Comparison

| Model | Size | Speed (CPU) | Quality | Best For |
|-------|------|-------------|---------|----------|
| **vit-gpt2** (current) | 500MB | ⚡⚡⚡ Fast | ⭐⭐ Poor | Quick testing |
| **BLIP-base** (recommended) | 990MB | ⚡⚡ Medium | ⭐⭐⭐⭐⭐ Excellent | Production |
| **BLIP-large** | 1.9GB | ⚡ Slow | ⭐⭐⭐⭐⭐ Best | High quality |
| **GIT-base** | 700MB | ⚡⚡ Medium | ⭐⭐⭐⭐ Very Good | Alternative |

---

## 🎯 Caption Quality Examples

### Image: Netflix Login Screenshot

**ViT-GPT2 (Current):**
> "A computer screen with a picture of a person on it"

**BLIP-base (Recommended):**
> "Netflix login page with email field and password field displayed on laptop screen"

**BLIP-large:**
> "Netflix login interface showing username field with 'hamza@example.com' and masked password field on a laptop display"

---

### Image: Code Screenshot

**ViT-GPT2 (Current):**
> "A computer screen with a picture of a computer"

**BLIP-base (Recommended):**
> "Computer terminal showing Python code with function definitions and syntax highlighting"

**BLIP-large:**
> "IDE window displaying Python code with function implementations, including variable assignments and control flow statements"

---

## 🚀 Quick Implementation (Copy-Paste Ready)

Want to switch to BLIP immediately? Follow these steps:

### 1. Create BLIP Service File

```bash
# Create the file
touch app/services/blip_caption_service.py
```

Copy the code from "Step 1" above into this file.

### 2. Update .env

```env
USE_LOCAL_VISION_MODEL=true
LOCAL_VISION_MODEL=Salesforce/blip-image-captioning-base
```

### 3. Modify GoogleDriveImageRAGActivity.py

Find this section (around line 163):

```python
# Generate caption using local model
local_service = get_local_caption_service()
```

Replace with:

```python
# Generate caption using local model
# Auto-detect model type from LOCAL_VISION_MODEL env var
model_name = os.getenv("LOCAL_VISION_MODEL", "").lower()

if "blip" in model_name:
    from app.services.blip_caption_service import get_blip_caption_service
    local_service = get_blip_caption_service()
    print(f"   🎨 Using BLIP model for better quality")
else:
    local_service = get_local_caption_service()
    print(f"   🤖 Using ViT-GPT2 model")
```

### 4. Restart Worker

```bash
python app/temporal/google_drive/workers/GoogleDriveMetaDataWorker.py
```

The BLIP model will download on first use (~990MB, 3-5 minutes).

---

## 🔍 Why BLIP is Better

### Technical Advantages:

1. **Better Architecture**: BLIP uses Vision Transformer + optimized language model
2. **More Training Data**: Trained on 129M image-text pairs
3. **Bootstrapping**: Uses synthetic captions to improve quality
4. **Text Detection**: Better at reading text in images

### Real-World Benefits:

- ✅ Recognizes objects accurately
- ✅ Describes scenes in detail
- ✅ Reads text from screenshots
- ✅ Less generic, more specific
- ✅ Better grammar and coherence

---

## ⚡ Performance Optimization Tips

### For Faster Processing:

1. **Reduce max_length:**
```python
caption = local_service.generate_caption(image, max_length=50)  # Faster
```

2. **Reduce num_beams:**
```python
# In generate() call
num_beams=2  # Faster but slightly lower quality
```

3. **Use smaller model:**
```env
LOCAL_VISION_MODEL=Salesforce/blip-image-captioning-base  # Not -large
```

### For Better Quality:

1. **Increase max_length:**
```python
caption = local_service.generate_caption(image, max_length=100)  # More detail
```

2. **Increase num_beams:**
```python
num_beams=8  # Better quality but slower
```

3. **Use larger model:**
```env
LOCAL_VISION_MODEL=Salesforce/blip-image-captioning-large
```

---

## 🐛 Troubleshooting

### Issue: Still getting generic captions with BLIP

**Solution:** Ensure you're passing high-resolution images (1024px). Check that `prefer_full_image=True`.

### Issue: BLIP model won't load

**Solution:** Clear cache and try again:
```bash
rm -rf ./model_cache
```

### Issue: Out of memory with BLIP

**Solution:** Use BLIP-base (not large) or reduce max_size to 512px.

---

## 📝 Summary

| Action | Result |
|--------|--------|
| **Keep ViT-GPT2** | Generic captions, fast processing |
| **Switch to BLIP-base** | ✅ Much better captions, reasonable speed |
| **Switch to BLIP-large** | ✅ Best captions, slower processing |

**Recommendation:** Switch to **BLIP-base** for significantly better results without major performance impact.

---

**Last Updated:** February 6, 2026  
**Version:** 3.0.0 (Model Upgrade Guide)
