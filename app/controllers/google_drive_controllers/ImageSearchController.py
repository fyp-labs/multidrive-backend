from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.services.google_drive_services.ImageSearchService import (
    search_images_by_text,
    get_image_caption,
    get_all_image_captions
)
from app.utils.keyword_extractor import extract_keywords
from pydantic import BaseModel, Field
from typing import Optional


class ImageSearchRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    google_drive_account_id: str = Field(..., description="Google Drive account ID")
    query: str = Field(..., description="Natural language search query", min_length=1)
    limit: Optional[int] = Field(10, description="Maximum number of results", ge=1, le=50)


class GetCaptionsRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    google_drive_account_id: str = Field(..., description="Google Drive account ID")
    skip: Optional[int] = Field(0, description="Number of records to skip", ge=0)
    limit: Optional[int] = Field(100, description="Maximum number of records", ge=1, le=500)


async def searchImages(db: Session, request: ImageSearchRequest):
    """
    Controller for searching images using natural language queries.
    """
    try:
        results = await search_images_by_text(
            db=db,
            user_id=request.user_id,
            google_drive_account_id=request.google_drive_account_id,
            query=request.query,
            limit=request.limit
        )
        
        return {
            "success": True,
            "query": request.query,
            "keywords": extract_keywords(request.query),
            "results_count": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search images: {str(e)}"
        )


async def getImageCaption(db: Session, file_id: str):
    """
    Controller for getting the caption of a specific image.
    """
    try:
        caption_data = await get_image_caption(db=db, file_id=file_id)
        
        if not caption_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No caption found for file_id: {file_id}"
            )
        
        return {
            "success": True,
            "caption": caption_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get image caption: {str(e)}"
        )


async def getAllImageCaptions(db: Session, request: GetCaptionsRequest):
    """
    Controller for getting all image captions for a user's Google Drive account.
    """
    try:
        captions = await get_all_image_captions(
            db=db,
            user_id=request.user_id,
            google_drive_account_id=request.google_drive_account_id,
            skip=request.skip,
            limit=request.limit
        )
        
        return {
            "success": True,
            "count": len(captions),
            "skip": request.skip,
            "limit": request.limit,
            "captions": captions
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get image captions: {str(e)}"
        )
