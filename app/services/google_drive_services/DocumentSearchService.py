from typing import List
from sqlalchemy.orm import Session
from app.config.chroma_client import search_similar_documents
from app.models.google_drive_models.GoogleDriveDocumentEmbeddingModel import GoogleDriveDocumentEmbedding
from app.models.google_drive_models.GoogleDriveFileModel import GoogleDriveFile


async def search_documents_by_text(
    db: Session,
    user_id: str,
    google_drive_account_ids: List[str],
    query: str,
    limit: int = 10
):
    """
    Search for documents using natural language queries across one or more
    Google Drive accounts. Uses ChromaDB for semantic search and PostgreSQL
    for detailed file information.

    Args:
        db: Database session
        user_id: User ID
        google_drive_account_ids: List of Google Drive account IDs to search
        query: Natural language search query
        limit: Maximum number of results to return

    Returns:
        List of search results with file details, text previews, relevance
        scores, and the `google_drive_account_id` each result came from.
    """
    chroma_results = search_similar_documents(
        user_id=user_id,
        google_drive_account_ids=google_drive_account_ids,
        query_text=query,
        n_results=limit
    )

    if not chroma_results["ids"] or not chroma_results["ids"][0]:
        return []

    metadatas = chroma_results["metadatas"][0]
    distances = chroma_results["distances"][0]

    file_ids = [metadata["file_id"] for metadata in metadatas]

    files = db.query(GoogleDriveFile).filter(
        GoogleDriveFile.file_id.in_(file_ids)
    ).all()

    embeddings = db.query(GoogleDriveDocumentEmbedding).filter(
        GoogleDriveDocumentEmbedding.file_id.in_(file_ids)
    ).all()

    file_map = {file.file_id: file for file in files}
    embedding_map = {emb.file_id: emb for emb in embeddings}

    search_results = []
    for i, _ in enumerate(file_ids):
        file = file_map.get(metadatas[i]["file_id"])
        embedding = embedding_map.get(metadatas[i]["file_id"])

        if file and embedding:
            search_results.append({
                "file_id": file.file_id,
                "file_name": file.file_name,
                "file_path": file.file_path,
                "mime_type": file.mime_type,
                "file_size": file.file_size,
                "created_time": file.file_created_time.isoformat() if file.file_created_time else None,
                "web_view_link": file.web_view_link,
                "google_drive_account_id": metadatas[i].get("google_drive_account_id"),
                "text_preview": embedding.text_preview,
                "word_count": embedding.word_count,
                "char_count": embedding.char_count,
                "extraction_metadata": embedding.extraction_metadata,
                "relevance_score": 1 - (distances[i] / 2),
                "distance": distances[i]
            })

    search_results.sort(key=lambda x: x["relevance_score"], reverse=True)

    return search_results


async def get_document_text(db: Session, file_id: str):
    """
    Get the extracted text for a specific document file.

    Args:
        db: Database session
        file_id: Google Drive file ID

    Returns:
        Document text data or None if not found
    """
    document_record = db.query(GoogleDriveDocumentEmbedding).filter(
        GoogleDriveDocumentEmbedding.file_id == file_id
    ).first()

    if not document_record:
        return None

    return {
        "file_id": document_record.file_id,
        "text_content": document_record.text_content,
        "text_preview": document_record.text_preview,
        "word_count": document_record.word_count,
        "char_count": document_record.char_count,
        "extraction_metadata": document_record.extraction_metadata,
        "created_at": document_record.created_at.isoformat() if document_record.created_at else None,
        "updated_at": document_record.updated_at.isoformat() if document_record.updated_at else None
    }


async def get_all_document_embeddings(
    db: Session,
    user_id: str,
    google_drive_account_ids: List[str],
    skip: int = 0,
    limit: int = 100
):
    """
    Get all document embeddings for a user across one or more Google Drive
    accounts.

    Args:
        db: Database session
        user_id: User ID
        google_drive_account_ids: List of Google Drive account IDs
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return

    Returns:
        List of document embedding records (each tagged with its account_id)
    """
    documents = db.query(GoogleDriveDocumentEmbedding).filter(
        GoogleDriveDocumentEmbedding.user_id == user_id,
        GoogleDriveDocumentEmbedding.google_drive_account_id.in_(google_drive_account_ids)
    ).offset(skip).limit(limit).all()

    results = []
    for doc in documents:
        results.append({
            "id": doc.id,
            "file_id": doc.file_id,
            "google_drive_account_id": doc.google_drive_account_id,
            "text_preview": doc.text_preview,
            "word_count": doc.word_count,
            "char_count": doc.char_count,
            "extraction_metadata": doc.extraction_metadata,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
        })

    return results
