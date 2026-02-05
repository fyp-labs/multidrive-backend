import os
import chromadb
import hashlib
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

# Configure ChromaDB client
def get_chroma_client():
    """
    Initialize and return a ChromaDB client.
    Uses persistent storage for embeddings.
    """
    chroma_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    
    client = chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    return client

def get_image_captions_collection(user_id: str, google_drive_account_id: str):
    """
    Get or create a ChromaDB collection for storing image captions and embeddings.
    Each user+account combination gets its own collection for isolation.
    """
    client = get_chroma_client()
    
    # Create a short, valid collection name using hash
    # Format: gdrive_imgs_{hash} - always valid and under 63 chars
    combined_id = f"{user_id}_{google_drive_account_id}"
    id_hash = hashlib.md5(combined_id.encode()).hexdigest()[:16]
    collection_name = f"gdrive_imgs_{id_hash}"
    
    try:
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={
                "user_id": user_id,
                "google_drive_account_id": google_drive_account_id,
                "description": "Image captions and embeddings for Google Drive files"
            }
        )
    except Exception as e:
        print(f"Error creating collection: {e}")
        raise
    
    return collection

def search_similar_images(user_id: str, google_drive_account_id: str, query_text: str, n_results: int = 10):
    """
    Search for similar images based on text query.
    
    Args:
        user_id: User ID
        google_drive_account_id: Google Drive account ID
        query_text: Text query to search for
        n_results: Number of results to return
    
    Returns:
        List of results with IDs, captions, and metadata
    """
    collection = get_image_captions_collection(user_id, google_drive_account_id)
    
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    
    return results
