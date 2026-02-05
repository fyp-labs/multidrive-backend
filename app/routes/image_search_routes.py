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
from app.services.google_drive_services.DocumentSearchService import (
    search_documents_by_text,
    get_document_text,
    get_all_document_embeddings
)
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(
    prefix="/api/image-search",
    tags=["Image Search & RAG"]
)

class DocumentSearchRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    google_drive_account_id: str = Field(..., description="Google Drive account ID")
    query: str = Field(..., description="Natural language search query", min_length=1)
    limit: Optional[int] = Field(10, description="Maximum number of results", ge=1, le=50)


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


# Document Search Endpoints

@router.post("/documents/search")
async def search_documents_endpoint(
    request: DocumentSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search for documents using natural language queries.
    
    This endpoint uses semantic search powered by document text extraction
    and ChromaDB vector embeddings to find relevant documents.
    
    **Example queries:**
    - "financial reports from 2023"
    - "meeting notes about project planning"
    - "documents containing pricing information"
    - "PDFs with technical specifications"
    
    Supports: PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), Text files
    
    Returns:
        List of matching documents with relevance scores, text previews, and file details
    """
    try:
        results = await search_documents_by_text(
            db=db,
            user_id=request.user_id,
            google_drive_account_id=request.google_drive_account_id,
            query=request.query,
            limit=request.limit
        )
        
        return {
            "success": True,
            "query": request.query,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search documents: {str(e)}"
        )


@router.get("/documents/text/{file_id}")
async def get_document_text_endpoint(
    file_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the extracted text for a specific document file.
    
    Args:
        file_id: Google Drive file ID
    
    Returns:
        Document text content, preview, and extraction metadata
    """
    try:
        document_data = await get_document_text(db=db, file_id=file_id)
        
        if not document_data:
            raise HTTPException(
                status_code=404,
                detail=f"No text found for file_id: {file_id}"
            )
        
        return {
            "success": True,
            "document": document_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document text: {str(e)}"
        )


@router.post("/documents/list")
async def list_all_documents_endpoint(
    request: GetCaptionsRequest,
    db: Session = Depends(get_db)
):
    """
    Get all document embeddings for a user's Google Drive account.
    
    Supports pagination through skip and limit parameters.
    
    Returns:
        List of all processed documents with text previews and metadata
    """
    try:
        documents = await get_all_document_embeddings(
            db=db,
            user_id=request.user_id,
            google_drive_account_id=request.google_drive_account_id,
            skip=request.skip,
            limit=request.limit
        )
        
        return {
            "success": True,
            "count": len(documents),
            "skip": request.skip,
            "limit": request.limit,
            "documents": documents
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get documents: {str(e)}"
        )
