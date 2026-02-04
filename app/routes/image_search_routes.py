from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.google_drive_controllers.ImageSearchController import (
    searchImages,
    getImageCaption,
    getAllImageCaptions,
    ImageSearchRequest,
    GetCaptionsRequest
)

router = APIRouter(
    prefix="/api/image-search",
    tags=["Image Search & RAG"]
)


@router.post("/search")
async def search_images_endpoint(
    request: ImageSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search for images using natural language queries.
    
    This endpoint uses semantic search powered by Gemini-generated captions
    and ChromaDB vector embeddings to find relevant images.
    
    **Example queries:**
    - "sunset beach photos"
    - "documents with charts and graphs"
    - "pictures of cats"
    - "screenshots with code"
    
    Returns:
        List of matching images with relevance scores, captions, and file details
    """
    return await searchImages(db=db, request=request)


@router.get("/caption/{file_id}")
async def get_image_caption_endpoint(
    file_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the AI-generated caption for a specific image file.
    
    Args:
        file_id: Google Drive file ID
    
    Returns:
        Caption data including text, metadata, and timestamps
    """
    return await getImageCaption(db=db, file_id=file_id)


@router.post("/captions/list")
async def list_all_captions_endpoint(
    request: GetCaptionsRequest,
    db: Session = Depends(get_db)
):
    """
    Get all image captions for a user's Google Drive account.
    
    Supports pagination through skip and limit parameters.
    
    Returns:
        List of all captions with metadata
    """
    return await getAllImageCaptions(db=db, request=request)
