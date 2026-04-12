# activities.py - Document RAG Pipeline Activity
from temporalio import activity
import asyncio
from functools import partial
from app.config.database import SessionLocal
from app.models.google_drive_models.GoogleDriveFileModel import GoogleDriveFile
from app.models.google_drive_models.GoogleDriveDocumentEmbeddingModel import GoogleDriveDocumentEmbedding
from app.config.chroma_client import get_chroma_client
from app.utils.fetch_google_drive_tokens import getGoogleDriveTokens
from app.utils.document_text_extractor import extract_text_from_document
import uuid
import hashlib
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


@activity.defn
async def process_documents_for_rag(input: dict):
    """
    Temporal activity to process documents through RAG pipeline:
    1. Fetch all document files from DB
    2. Download and extract text from documents
    3. Create embeddings and store in ChromaDB
    4. Save text content and metadata to PostgreSQL
    
    Args:
        input: dict with user_id and google_drive_account_id
    """
    activity.heartbeat({"step": "init", "message": "Starting document RAG pipeline"})
    
    user_id = input.get("user_id")
    google_drive_account_id = input.get("google_drive_account_id")
    
    loop = asyncio.get_running_loop()
    
    # Get Google Drive OAuth tokens
    activity.heartbeat({"step": "fetch_tokens", "message": "Fetching Google Drive tokens"})
    tokens = await getGoogleDriveTokens({
        "user_id": user_id,
        "google_drive_account_id": google_drive_account_id
    })
    
    if not tokens:
        return {
            "message": "Failed to retrieve Google Drive tokens",
            "total_documents": 0,
            "processed": 0,
            "failed": 0,
            "success_rate": "0%"
        }
    
    access_token = tokens.get("access_token")
    print(f"✅ Retrieved access token for documents")
    
    # Step 1: Fetch all document files from database
    activity.heartbeat({"step": "fetch_documents", "message": "Fetching document files from database"})
    
    def get_document_files_sync():
        with SessionLocal() as db:
            # Query for document files (excluding images and code files)
            document_mime_types = [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
                'application/msword',  # .doc
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
                'application/vnd.ms-excel',  # .xls
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
                'application/vnd.ms-powerpoint',  # .ppt
                'text/plain',  # .txt
            ]
            
            return db.query(
                GoogleDriveFile.file_id,
                GoogleDriveFile.file_name,
                GoogleDriveFile.file_path,
                GoogleDriveFile.mime_type,
                GoogleDriveFile.file_size
            ).filter(
                GoogleDriveFile.user_id == user_id,
                GoogleDriveFile.google_drive_account_id == google_drive_account_id,
                GoogleDriveFile.mime_type.in_(document_mime_types)
            ).all()
    
    document_files = await loop.run_in_executor(None, get_document_files_sync)
    
    total_documents = len(document_files)
    activity.heartbeat({
        "step": "fetch_documents_complete",
        "message": f"Found {total_documents} document files"
    })
    
    if total_documents == 0:
        return {
            "message": "No documents found to process",
            "total_processed": 0
        }
    
    # Step 2: Get ChromaDB collection for documents
    activity.heartbeat({"step": "init_chroma", "message": "Initializing ChromaDB collection for documents"})
    
    def get_collection_sync():
        client = get_chroma_client()
        # Create a short, valid collection name using hash
        # Format: gdrive_docs_{hash} - always valid and under 63 chars
        combined_id = f"{user_id}_{google_drive_account_id}"
        id_hash = hashlib.md5(combined_id.encode()).hexdigest()[:16]
        collection_name = f"gdrive_docs_{id_hash}"
        
        return client.get_or_create_collection(
            name=collection_name,
            metadata={
                "user_id": user_id,
                "google_drive_account_id": google_drive_account_id,
                "description": "Document text embeddings for Google Drive files"
            }
        )
    
    collection = await loop.run_in_executor(None, get_collection_sync)
    
    # Step 3: Process documents in batches
    batch_size = 3  # Smaller batch for documents (larger files)
    delay_between_docs = 1  # Delay between documents
    processed_count = 0
    failed_count = 0
    embeddings_to_save = []
    
    # Build Drive service
    credentials = Credentials(token=access_token)
    service = build('drive', 'v3', credentials=credentials)
    
    for i in range(0, total_documents, batch_size):
        batch = document_files[i:i + batch_size]
        
        activity.heartbeat({
            "step": "processing_batch",
            "batch": i // batch_size + 1,
            "total_batches": (total_documents + batch_size - 1) // batch_size,
            "processed": processed_count,
            "failed": failed_count
        })
        
        # Process each document in the batch
        for file in batch:
            try:
                file_id = file.file_id
                file_name = file.file_name
                file_path = file.file_path
                mime_type = file.mime_type
                file_size = file.file_size
                
                activity.heartbeat({
                    "step": "processing_document",
                    "file_name": file_name,
                    "processed": processed_count + 1,
                    "total": total_documents
                })
                
                print(f"📄 Processing document: {file_name}")
                print(f"   Type: {mime_type}, Size: {file_size} bytes")
                
                # Download file content
                activity.heartbeat({
                    "step": "downloading_document",
                    "file_name": file_name,
                    "file_size": file_size
                })
                
                def download_file_sync():
                    request = service.files().get_media(fileId=file_id)
                    return request.execute()
                
                file_content = await loop.run_in_executor(None, download_file_sync)
                print(f"   📥 Downloaded {len(file_content)} bytes")
                
                # Send heartbeat after download
                activity.heartbeat({
                    "step": "extracting_text",
                    "file_name": file_name,
                    "downloaded_bytes": len(file_content)
                })
                
                # Extract text from document
                text_content, extraction_meta = extract_text_from_document(
                    file_content, 
                    mime_type, 
                    file_name
                )
                
                if not text_content or len(text_content.strip()) < 50:
                    print(f"   ⚠️ Document has insufficient text content, skipping")
                    failed_count += 1
                    continue
                
                # Truncate text for storage (keep first 10000 chars)
                stored_text = text_content[:10000]
                text_preview = text_content[:500] + "..." if len(text_content) > 500 else text_content
                
                word_count = len(text_content.split())
                char_count = len(text_content)
                
                print(f"   📝 Extracted {word_count} words, {char_count} characters")
                
                # Send heartbeat after text extraction
                activity.heartbeat({
                    "step": "creating_embedding",
                    "file_name": file_name,
                    "word_count": word_count
                })
                
                # Generate unique ChromaDB document ID
                chroma_doc_id = f"{user_id}_{google_drive_account_id}_{file_id}_doc"
                
                # Add to ChromaDB with automatic embedding
                def add_to_chroma_sync():
                    collection.add(
                        documents=[text_content],  # Full text for embedding
                        ids=[chroma_doc_id],
                        metadatas=[{
                            "file_id": file_id,
                            "file_name": file_name,
                            "file_path": file_path,
                            "mime_type": mime_type,
                            "user_id": user_id,
                            "google_drive_account_id": google_drive_account_id,
                            "word_count": word_count,
                            "char_count": char_count
                        }]
                    )
                
                await loop.run_in_executor(None, add_to_chroma_sync)
                print(f"   ✅ Added to ChromaDB")
                
                # Send heartbeat after ChromaDB addition
                activity.heartbeat({
                    "step": "saving_metadata",
                    "file_name": file_name,
                    "processed": processed_count + 1
                })
                
                # Prepare embedding data for PostgreSQL
                embeddings_to_save.append({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "google_drive_account_id": google_drive_account_id,
                    "file_id": file_id,
                    "text_content": stored_text,
                    "text_preview": text_preview,
                    "chroma_doc_id": chroma_doc_id,
                    "extraction_metadata": extraction_meta,
                    "word_count": word_count,
                    "char_count": char_count
                })
                
                processed_count += 1
                print(f"   ✅ Document {processed_count}/{total_documents} completed successfully")
                
                # Send heartbeat after successful completion
                activity.heartbeat({
                    "step": "document_completed",
                    "file_name": file_name,
                    "processed": processed_count,
                    "failed": failed_count,
                    "total": total_documents
                })
                
                # Add delay between documents
                if processed_count + failed_count < total_documents:
                    print(f"   ⏳ Waiting {delay_between_docs}s...")
                    await asyncio.sleep(delay_between_docs)
                
            except Exception as e:
                failed_count += 1
                error_details = {
                    "step": "processing_error",
                    "file_name": file.file_name,
                    "file_id": file.file_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "failed": failed_count
                }
                activity.heartbeat(error_details)
                print(f"❌ Error processing {file.file_name}: {type(e).__name__} - {str(e)}")
                continue
        
        # Save batch of embeddings to database
        if embeddings_to_save:
            activity.heartbeat({
                "step": "saving_embeddings",
                "count": len(embeddings_to_save)
            })
            
            def save_embeddings_sync(embeddings_data):
                with SessionLocal() as db:
                    try:
                        stmt = insert(GoogleDriveDocumentEmbedding).values(embeddings_data)
                        upsert_stmt = stmt.on_conflict_do_update(
                            index_elements=["file_id"],
                            set_={
                                "text_content": stmt.excluded.text_content,
                                "text_preview": stmt.excluded.text_preview,
                                "chroma_doc_id": stmt.excluded.chroma_doc_id,
                                "extraction_metadata": stmt.excluded.extraction_metadata,
                                "word_count": stmt.excluded.word_count,
                                "char_count": stmt.excluded.char_count,
                                "updated_at": datetime.now(timezone.utc)
                            }
                        )
                        db.execute(upsert_stmt)
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        raise e
            
            await loop.run_in_executor(None, partial(save_embeddings_sync, embeddings_to_save))
            embeddings_to_save = []  # Clear batch
    
    activity.heartbeat({
        "step": "complete",
        "message": "Document RAG pipeline completed",
        "processed": processed_count,
        "failed": failed_count
    })
    
    return {
        "message": "Document RAG pipeline completed successfully",
        "total_documents": total_documents,
        "processed": processed_count,
        "failed": failed_count,
        "success_rate": f"{(processed_count / total_documents * 100):.2f}%" if total_documents > 0 else "0%"
    }
