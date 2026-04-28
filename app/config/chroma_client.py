import os
import chromadb
import hashlib
from typing import List
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


def _image_collection_name(user_id: str, google_drive_account_id: str) -> str:
    combined_id = f"{user_id}_{google_drive_account_id}"
    id_hash = hashlib.md5(combined_id.encode()).hexdigest()[:16]
    return f"gdrive_imgs_{id_hash}"


def _document_collection_name(user_id: str, google_drive_account_id: str) -> str:
    combined_id = f"{user_id}_{google_drive_account_id}"
    id_hash = hashlib.md5(combined_id.encode()).hexdigest()[:16]
    return f"gdrive_docs_{id_hash}"


def get_image_captions_collection(user_id: str, google_drive_account_id: str):
    """
    Get or create a ChromaDB collection for storing image captions and embeddings.
    Each user+account combination gets its own collection for isolation.
    """
    client = get_chroma_client()
    collection_name = _image_collection_name(user_id, google_drive_account_id)

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


def search_similar_images(user_id: str, google_drive_account_ids: List[str], query_text: str, n_results: int = 10):
    """
    Search for similar images across one or more Google Drive accounts.
    Each account has its own ChromaDB collection — we query each, merge,
    sort by distance, and trim to n_results.

    Each metadata dict in the merged result is stamped with
    `google_drive_account_id` so callers can attribute results to accounts.

    Returns a dict matching ChromaDB's batch query shape (single-query):
    {"ids": [[...]], "documents": [[...]], "metadatas": [[...]], "distances": [[...]]}
    """
    client = get_chroma_client()

    all_ids: List[str] = []
    all_docs: List[str] = []
    all_metas: List[dict] = []
    all_dists: List[float] = []

    for account_id in google_drive_account_ids:
        collection_name = _image_collection_name(user_id, account_id)
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            # Collection doesn't exist for this account yet — skip it
            continue

        res = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        ids = (res.get("ids") or [[]])[0] or []
        docs = (res.get("documents") or [[]])[0] or []
        metas = (res.get("metadatas") or [[]])[0] or []
        dists = (res.get("distances") or [[]])[0] or []

        for m in metas:
            m["google_drive_account_id"] = account_id

        all_ids.extend(ids)
        all_docs.extend(docs)
        all_metas.extend(metas)
        all_dists.extend(dists)

    if not all_ids:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    combined = sorted(
        zip(all_ids, all_docs, all_metas, all_dists),
        key=lambda x: x[3]  # distance ascending (lower = more similar)
    )[:n_results]

    ids, docs, metas, dists = zip(*combined)
    return {
        "ids": [list(ids)],
        "documents": [list(docs)],
        "metadatas": [list(metas)],
        "distances": [list(dists)],
    }


def search_similar_documents(user_id: str, google_drive_account_ids: List[str], query_text: str, n_results: int = 10):
    """
    Search for similar documents across one or more Google Drive accounts.
    Mirrors `search_similar_images` but uses the document collection naming.
    """
    client = get_chroma_client()

    all_ids: List[str] = []
    all_docs: List[str] = []
    all_metas: List[dict] = []
    all_dists: List[float] = []

    for account_id in google_drive_account_ids:
        collection_name = _document_collection_name(user_id, account_id)
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            continue

        res = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        ids = (res.get("ids") or [[]])[0] or []
        docs = (res.get("documents") or [[]])[0] or []
        metas = (res.get("metadatas") or [[]])[0] or []
        dists = (res.get("distances") or [[]])[0] or []

        for m in metas:
            m["google_drive_account_id"] = account_id

        all_ids.extend(ids)
        all_docs.extend(docs)
        all_metas.extend(metas)
        all_dists.extend(dists)

    if not all_ids:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    combined = sorted(
        zip(all_ids, all_docs, all_metas, all_dists),
        key=lambda x: x[3]
    )[:n_results]

    ids, docs, metas, dists = zip(*combined)
    return {
        "ids": [list(ids)],
        "documents": [list(docs)],
        "metadatas": [list(metas)],
        "distances": [list(dists)],
    }
