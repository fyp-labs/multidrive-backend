from sqlalchemy.orm import Session
from app.config.chroma_client import search_similar_images
from app.models.google_drive_models.GoogleDriveImageCaptionModel import GoogleDriveImageCaption
from app.models.google_drive_models.GoogleDriveFileModel import GoogleDriveFile


async def search_images_by_text(
    db: Session,
    user_id: str,
    google_drive_account_id: str,
    query: str,
    limit: int = 10
):
    """
    Search for images using natural language queries.
    Uses ChromaDB for semantic search and PostgreSQL for detailed file information.
    
    Args:
        db: Database session
        user_id: User ID
        google_drive_account_id: Google Drive account ID
        query: Natural language search query
        limit: Maximum number of results to return
    
    Returns:
        List of search results with file details, captions, and relevance scores
    """
    # Step 1: Perform semantic search in ChromaDB
    chroma_results = search_similar_images(
        user_id=user_id,
        google_drive_account_id=google_drive_account_id,
        query_text=query,
        n_results=limit
    )
    
    # Step 2: Extract file IDs from ChromaDB results
    if not chroma_results["ids"] or not chroma_results["ids"][0]:
        return []
    
    result_ids = chroma_results["ids"][0]
    captions = chroma_results["documents"][0]
    metadatas = chroma_results["metadatas"][0]
    distances = chroma_results["distances"][0]
    
    # Extract file_ids from metadata
    file_ids = [metadata["file_id"] for metadata in metadatas]
    
    # Step 3: Fetch detailed file information from PostgreSQL
    files = db.query(GoogleDriveFile).filter(
        GoogleDriveFile.file_id.in_(file_ids)
    ).all()
    
    # Create a map of file_id to file object for quick lookup
    file_map = {file.file_id: file for file in files}
    
    # Step 4: Combine results
    search_results = []
    for i, file_id in enumerate(file_ids):
        file = file_map.get(metadatas[i]["file_id"])
        if file:
            search_results.append({
                "file_id": file.file_id,
                "file_name": file.file_name,
                "file_path": file.file_path,
                "mime_type": file.mime_type,
                "file_size": file.file_size,
                "created_time": file.file_created_time.isoformat() if file.file_created_time else None,
                "thumbnail_link": file.thumbnail_link,
                "web_view_link": file.web_view_link,
                "caption": captions[i],
                "relevance_score": 1 - (distances[i] / 2),  # Convert distance to similarity score (0-1)
                "distance": distances[i]
            })
    
    # Sort by relevance score (highest first)
    search_results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return search_results


async def get_image_caption(db: Session, file_id: str):
    """
    Get the caption for a specific image file.
    
    Args:
        db: Database session
        file_id: Google Drive file ID
    
    Returns:
        Caption data or None if not found
    """
    caption_record = db.query(GoogleDriveImageCaption).filter(
        GoogleDriveImageCaption.file_id == file_id
    ).first()
    
    if not caption_record:
        return None
    
    return {
        "file_id": caption_record.file_id,
        "caption": caption_record.caption,
        "chroma_doc_id": caption_record.chroma_doc_id,
        "metadata": caption_record.file_metadata,
        "created_at": caption_record.created_at.isoformat() if caption_record.created_at else None,
        "updated_at": caption_record.updated_at.isoformat() if caption_record.updated_at else None
    }


async def get_all_image_captions(
    db: Session,
    user_id: str,
    google_drive_account_id: str,
    skip: int = 0,
    limit: int = 100
):
    """
    Get all image captions for a user's Google Drive account.
    
    Args:
        db: Database session
        user_id: User ID
        google_drive_account_id: Google Drive account ID
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
    
    Returns:
        List of caption records
    """
    captions = db.query(GoogleDriveImageCaption).filter(
        GoogleDriveImageCaption.user_id == user_id,
        GoogleDriveImageCaption.google_drive_account_id == google_drive_account_id
    ).offset(skip).limit(limit).all()
    
    results = []
    for caption in captions:
        results.append({
            "id": caption.id,
            "file_id": caption.file_id,
            "caption": caption.caption,
            "metadata": caption.file_metadata,
            "created_at": caption.created_at.isoformat() if caption.created_at else None,
            "updated_at": caption.updated_at.isoformat() if caption.updated_at else None
        })
    
    return results
