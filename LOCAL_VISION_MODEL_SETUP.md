# Local Vision Model Setup Guide

## Overview

This guide explains the new local image captioning feature that replaces Gemini API with a CPU-friendly vision-language model.

---

## ✅ What Was Changed

### 1. **New Service Created**
- **File**: `app/services/local_caption_service.py`
- **Purpose**: Handles image captioning using local HuggingFace models
- **Features**:
  - Singleton pattern (model loads once)
  - Lazy loading (loads on first use, not at startup)
  - CPU-only execution
  - Thread-safe implementation
  - Comprehensive error handling

### 2. **Modified Files**

#### `app/temporal/google_drive/activities/GoogleDriveImageRAGActivity.py`
- Added import for `download_thumbnail` from `gemini_client`
- Added import for `get_local_caption_service`
- Added import for `os` module
- Modified caption generation logic (lines 142-177):
  - Checks `USE_LOCAL_VISION_MODEL` environment variable
  - Routes to **LocalCaptionService** when `USE_LOCAL_VISION_MODEL=true`
  - Routes to **Gemini API** when `USE_LOCAL_VISION_MODEL=false`
  - Preserves all existing functionality

#### `requirements.txt`
- Added 3 new dependencies:
  ```
  torch==2.5.1
  transformers==4.46.3
  accelerate==1.2.1
  ```

#### `.env`
- Added vision model configuration section:
  ```
  USE_LOCAL_VISION_MODEL=true
  LOCAL_VISION_MODEL=nlpconnect/vit-gpt2-image-captioning
  MODEL_CACHE_DIR=./model_cache
  ```

---

## 🚀 Installation

### Step 1: Install Dependencies

```bash
pip install torch==2.5.1 transformers==4.46.3 accelerate==1.2.1
```

**Note**: This will download ~2.5GB of packages. The installation may take 5-10 minutes on a typical connection.

### Step 2: Configure Environment

Your `.env` file is already configured correctly:
```
USE_LOCAL_VISION_MODEL=true
LOCAL_VISION_MODEL=nlpconnect/vit-gpt2-image-captioning
MODEL_CACHE_DIR=./model_cache
```

### Step 3: First Run

On first run, the model will be downloaded automatically:
- **Model size**: ~500MB
- **Download location**: `./model_cache` directory
- **Download time**: 2-5 minutes (depending on internet speed)

The model downloads **only once** and is cached for future use.

---

## 📋 Usage

### Switch Between Local Model and Gemini API

Edit your `.env` file:

**Use Local Model (CPU, no API costs):**
```env
USE_LOCAL_VISION_MODEL=true
```

**Use Gemini API (requires API key):**
```env
USE_LOCAL_VISION_MODEL=false
```

Then restart your FastAPI server.

---

## 🔍 How It Works

### Architecture

```
Image RAG Pipeline
    │
    ├─ Download thumbnail from Google Drive
    │
    ├─ Check USE_LOCAL_VISION_MODEL
    │
    ├─ If TRUE:
    │   └─ LocalCaptionService (CPU-based)
    │       ├─ Load model (lazy, first time only)
    │       ├─ Process image through ViT encoder
    │       ├─ Generate caption with GPT-2 decoder
    │       └─ Return caption text
    │
    └─ If FALSE:
        └─ Gemini API (original behavior)
            └─ Send image to Gemini API
            └─ Return caption text
    │
    └─ Store caption in ChromaDB & PostgreSQL
```

### Model Details

**Model**: `nlpconnect/vit-gpt2-image-captioning`

- **Vision Encoder**: ViT (Vision Transformer)
  - Trained on ImageNet
  - Converts images to feature vectors

- **Language Decoder**: GPT-2
  - Generates natural language captions
  - Trained on image-caption pairs

- **Performance**:
  - **Speed**: ~2-3 seconds per image on i5 CPU
  - **Quality**: Good for general scene understanding
  - **Memory**: ~1GB RAM during inference

---

## ⚙️ Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_LOCAL_VISION_MODEL` | `false` | Enable local model (`true`/`false`) |
| `LOCAL_VISION_MODEL` | `nlpconnect/vit-gpt2-image-captioning` | HuggingFace model name |
| `MODEL_CACHE_DIR` | `./model_cache` | Local cache directory for models |

### Switching Models

You can use different HuggingFace models by changing `LOCAL_VISION_MODEL`:

```env
# Option 1: Current model (recommended for CPU)
LOCAL_VISION_MODEL=nlpconnect/vit-gpt2-image-captioning

# Option 2: Larger model (better quality, slower)
LOCAL_VISION_MODEL=Salesforce/blip-image-captioning-base

# Option 3: Microsoft Florence (more detailed)
LOCAL_VISION_MODEL=microsoft/Florence-2-base
```

**Note**: Different models may require code adjustments in `LocalCaptionService.generate_caption()`.

---

## 🧪 Testing

### Test Local Caption Service

Create a test script `test_local_caption.py`:

```python
import asyncio
from PIL import Image
from app.services.local_caption_service import get_local_caption_service

async def test_caption():
    # Load test image
    image = Image.open("path/to/test_image.jpg")
    
    # Get service
    service = get_local_caption_service()
    
    # Generate caption
    caption = await asyncio.get_event_loop().run_in_executor(
        None,
        service.generate_caption,
        image
    )
    
    print(f"Caption: {caption}")

if __name__ == "__main__":
    asyncio.run(test_caption())
```

### Test RAG Pipeline

Use your existing `test_rag_pipeline.py` with `USE_LOCAL_VISION_MODEL=true` in `.env`.

---

## 📊 Performance Comparison

| Feature | Local Model | Gemini API |
|---------|-------------|------------|
| **Speed** | ~2-3 sec/image | ~1-2 sec/image |
| **Cost** | Free | Pay per request |
| **Quality** | Good | Excellent |
| **Internet** | Only for download | Required always |
| **Privacy** | All local | Data sent to Google |
| **GPU** | Not required | N/A |
| **RAM** | ~1GB | N/A |

---

## 🛠️ Troubleshooting

### Issue: Model won't load

**Solution**: Check available disk space (~500MB needed) and RAM (1GB+ needed)

```bash
# Check disk space
df -h

# Clear cache and re-download
rm -rf ./model_cache
```

### Issue: Out of memory

**Solution**: Close other applications or reduce batch size in `GoogleDriveImageRAGActivity.py`:

```python
batch_size = 3  # Reduced from 5
```

### Issue: Very slow performance

**Solution**: 
1. Check CPU usage (Task Manager)
2. Ensure no other heavy processes running
3. Consider switching to Gemini API for large batches

### Issue: Import errors

**Solution**: Reinstall dependencies:

```bash
pip uninstall torch transformers accelerate
pip install torch==2.5.1 transformers==4.46.3 accelerate==1.2.1
```

---

## 📝 Code Structure

### LocalCaptionService Class

```python
class LocalCaptionService:
    """
    Singleton service for local image captioning.
    
    Methods:
    - generate_caption(image: Image.Image) -> str
    - is_loaded() -> bool
    - get_model_info() -> dict
    """
```

### Integration Points

1. **Activity File** (`GoogleDriveImageRAGActivity.py`):
   - Checks environment variable
   - Routes to appropriate service
   - Handles async execution

2. **Service File** (`local_caption_service.py`):
   - Loads model lazily
   - Generates captions
   - Thread-safe singleton

3. **Config File** (`.env`):
   - Controls which service to use
   - Sets model configuration

---

## ✨ Key Features

✅ **Singleton Pattern**: Model loads once, reused across all requests
✅ **Lazy Loading**: Model loads on first use, not at startup
✅ **CPU-Optimized**: Explicitly configured for CPU execution
✅ **Error Handling**: Comprehensive error messages and graceful degradation
✅ **Thread-Safe**: Safe for concurrent requests
✅ **Production-Ready**: Logging, monitoring, and error recovery
✅ **Backward Compatible**: Doesn't break existing Gemini integration
✅ **Easy Switching**: Toggle between models via environment variable

---

## 🎯 Best Practices

1. **Development**: Use local model to avoid API costs
2. **Production**: Use Gemini API for better quality (if budget allows)
3. **Hybrid**: Use local model for bulk processing, Gemini for important images
4. **Monitoring**: Check logs for model loading and caption generation times
5. **Caching**: Keep `model_cache` directory in `.gitignore`

---

## 📚 Additional Resources

- [HuggingFace Model Card](https://huggingface.co/nlpconnect/vit-gpt2-image-captioning)
- [Vision Transformer Paper](https://arxiv.org/abs/2010.11929)
- [GPT-2 Documentation](https://huggingface.co/gpt2)

---

## 🔄 Future Enhancements

Potential improvements:
- [ ] Add GPU support for faster inference
- [ ] Implement batch processing for multiple images
- [ ] Add model warm-up at startup (optional)
- [ ] Support for multiple models simultaneously
- [ ] Add caption quality scoring
- [ ] Implement caching for generated captions

---

## ❓ FAQ

**Q: Can I use GPU if available?**
A: Yes, modify `local_caption_service.py` line 51:
```python
self.device = "cuda" if torch.cuda.is_available() else "cpu"
```

**Q: How do I use a different model?**
A: Change `LOCAL_VISION_MODEL` in `.env` and ensure the model is compatible with VisionEncoderDecoderModel.

**Q: Does this affect document RAG?**
A: No, only image captioning is affected. Document text extraction and embeddings remain unchanged.

**Q: Can I run both models simultaneously?**
A: Not currently. You must choose one via `USE_LOCAL_VISION_MODEL`.

---

## 📞 Support

For issues or questions:
1. Check logs in console output
2. Verify `.env` configuration
3. Ensure all dependencies installed correctly
4. Check system resources (RAM, disk space)

---

**Last Updated**: February 6, 2026
**Version**: 1.0.0
