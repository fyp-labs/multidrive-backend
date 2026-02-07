import os
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
import io
import httpx
import asyncio
import time
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

load_dotenv()

# Get model name from environment or use default
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Configure Gemini API
def configure_gemini():
    """Configure the Gemini API with API key from environment"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    genai.configure(api_key=api_key)

def get_gemini_model(model_name: str = None):
    """
    Get a Gemini model instance.
    
    Args:
        model_name: Name of the model to use (defaults to GEMINI_MODEL env var or gemini-2.5-flash)
    
    Returns:
        Configured Gemini model
    """
    configure_gemini()
    if model_name is None:
        model_name = DEFAULT_GEMINI_MODEL
    print(f"   🤖 Using Gemini model: {model_name}")
    return genai.GenerativeModel(model_name)

async def download_thumbnail_via_api(file_id: str, access_token: str, max_size: int = 1024) -> Image.Image:
    """
    Download image using Google Drive API directly (fallback method).
    Downloads full-resolution image for better caption quality.
    
    Args:
        file_id: Google Drive file ID
        access_token: OAuth access token
        max_size: Maximum dimension for resizing (default: 1024px for better quality)
    
    Returns:
        PIL Image object
    """
    try:
        print(f"   📥 Fetching full image via Drive API (file_id: {file_id[:20]}...)...")
        
        # Create credentials from access token
        credentials = Credentials(token=access_token)
        
        # Build Drive service
        service = build('drive', 'v3', credentials=credentials)
        
        # Get full image content (not thumbnail)
        request = service.files().get_media(fileId=file_id)
        
        # Execute in thread pool since it's blocking
        loop = asyncio.get_running_loop()
        file_content = await loop.run_in_executor(None, request.execute)
        
        # Convert to PIL Image
        image_bytes = io.BytesIO(file_content)
        image = Image.open(image_bytes)
        
        original_size = image.size
        print(f"   📥 Full image downloaded: {original_size}, format: {image.format}")
        
        # Resize if image is very large (for memory efficiency while maintaining quality)
        if image.size[0] > max_size or image.size[1] > max_size:
            print(f"   🔄 Resizing from {original_size} to fit {max_size}px (maintaining aspect ratio)...")
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            print(f"   ✅ Resized to: {image.size}")
        
        return image
        
    except Exception as e:
        print(f"   ❌ API download failed: {type(e).__name__} - {str(e)}")
        raise

async def download_thumbnail(thumbnail_url: str, access_token: str = None, file_id: str = None, prefer_full_image: bool = False, max_size: int = 1024) -> Image.Image:
    """
    Download an image from Google Drive with fallback to full image via API.
    
    Args:
        thumbnail_url: URL of the thumbnail to download
        access_token: OAuth access token for authenticated requests (required for Google Drive)
        file_id: Google Drive file ID (for fallback method)
        prefer_full_image: If True, skip thumbnail and download full image directly via API (better quality)
        max_size: Maximum dimension for resizing full images (default: 1024px)
    
    Returns:
        PIL Image object
    """
    # If prefer_full_image is True and we have the necessary credentials, skip thumbnail URL
    if prefer_full_image and file_id and access_token:
        print(f"   📥 Downloading full-resolution image (skipping thumbnail URL)...")
        return await download_thumbnail_via_api(file_id, access_token, max_size)
    
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"   📥 Downloading thumbnail... (Auth: {'Yes' if access_token else 'No'})")
            response = await client.get(thumbnail_url, headers=headers, timeout=30.0)
            print(f"   📥 Response status: {response.status_code}")
            
            # If 403 Forbidden and we have file_id, try API fallback
            if response.status_code == 403 and file_id and access_token:
                print(f"   ⚠️ 403 Forbidden - Trying full image download via Drive API...")
                return await download_thumbnail_via_api(file_id, access_token, max_size)
            
            response.raise_for_status()
            
            image_bytes = io.BytesIO(response.content)
            print(f"   📥 Downloaded {len(response.content)} bytes")
            image = Image.open(image_bytes)
            print(f"   📥 Image loaded: {image.size}, format: {image.format}")
            
            return image
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403 and file_id and access_token:
            print(f"   ⚠️ 403 Forbidden - Trying full image download via Drive API...")
            return await download_thumbnail_via_api(file_id, access_token, max_size)
        print(f"   ❌ Download failed: {type(e).__name__} - {str(e)}")
        raise
    except Exception as e:
        print(f"   ❌ Download failed: {type(e).__name__} - {str(e)}")
        raise

async def generate_image_caption(image: Image.Image, model_name: str = None, max_retries: int = 3) -> str:
    """
    Generate a caption for an image using Gemini Vision API with retry logic.
    
    Args:
        image: PIL Image object
        model_name: Gemini model to use
        max_retries: Maximum number of retry attempts for rate limits
    
    Returns:
        Generated caption as string
    """
    model = get_gemini_model(model_name)
    
    prompt = """Analyze this image and provide a detailed, descriptive caption. 
    Focus on:
    - Main subjects and objects in the image
    - Colors, composition, and visual style
    - Context and setting
    - Any text visible in the image
    - Overall mood or theme
    
    Keep the caption concise but informative (2-3 sentences)."""
    
    for attempt in range(max_retries):
        try:
            print(f"   🤖 Sending to Gemini API (attempt {attempt + 1}/{max_retries})...")
            response = model.generate_content([prompt, image])
            caption = response.text.strip()
            print(f"   🤖 Gemini response received")
            return caption
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a rate limit error
            is_rate_limit = any(keyword in error_str for keyword in [
                'rate limit', 'quota', 'resource_exhausted', '429', 'too many requests'
            ])
            
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                print(f"   ⏳ Rate limit detected. Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
                continue
            else:
                print(f"   ❌ Gemini API failed: {type(e).__name__} - {str(e)}")
                raise Exception(f"Failed to generate caption after {attempt + 1} attempts: {str(e)}")

async def generate_caption_from_url(thumbnail_url: str, model_name: str = None, access_token: str = None, file_id: str = None, max_retries: int = 3) -> str:
    """
    Download an image from URL and generate its caption with retry logic and API fallback.
    
    Args:
        thumbnail_url: URL of the thumbnail
        model_name: Gemini model to use
        access_token: OAuth access token for authenticated requests (required for Google Drive)
        file_id: Google Drive file ID (for API fallback when thumbnail URL fails)
        max_retries: Maximum number of retry attempts
    
    Returns:
        Generated caption
    """
    image = await download_thumbnail(thumbnail_url, access_token, file_id)
    caption = await generate_image_caption(image, model_name, max_retries)
    return caption
