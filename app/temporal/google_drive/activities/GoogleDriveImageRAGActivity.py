# activities.py - Image RAG Pipeline Activity
from temporalio import activity
import asyncio
from functools import partial
from app.config.database import SessionLocal
from app.models.google_drive_models.GoogleDriveFileModel import GoogleDriveFile
from app.models.google_drive_models.GoogleDriveImageCaptionModel import GoogleDriveImageCaption
from app.config.gemini_client import generate_caption_from_url, download_thumbnail
from app.services.local_caption_service import get_local_caption_service
from app.services.blip_caption_service import get_blip_caption_service
from app.config.chroma_client import get_image_captions_collection
from app.utils.fetch_google_drive_tokens import getGoogleDriveTokens
import uuid
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone
import os


@activity.defn
async def process_images_for_rag(input: dict):
    """
    Temporal activity to process images through RAG pipeline:
    1. Fetch all image files with thumbnails from DB
    2. Download thumbnails and generate captions using Gemini
    3. Create embeddings and store in ChromaDB
    4. Save caption metadata to PostgreSQL
    
    Args:
        input: dict with user_id and google_drive_account_id
    """
    activity.heartbeat({"step": "init", "message": "Starting image RAG pipeline"})
    
    user_id = input.get("user_id")
    google_drive_account_id = input.get("google_drive_account_id")
    
    loop = asyncio.get_running_loop()
    
    # Get Google Drive OAuth tokens for authenticated thumbnail downloads
    activity.heartbeat({"step": "fetch_tokens", "message": "Fetching Google Drive tokens"})
    tokens = await getGoogleDriveTokens({
        "user_id": user_id,
        "google_drive_account_id": google_drive_account_id
    })
    
    if not tokens:
        return {
            "message": "Failed to retrieve Google Drive tokens",
            "total_images": 0,
            "processed": 0,
            "failed": 0,
            "success_rate": "0%"
        }
    
    access_token = tokens.get("access_token")
    if access_token:
        print(f"✅ Retrieved access token for images (length: {len(access_token)} chars)")
    else:
        print(f"❌ No access token retrieved!")
    
    # Step 1: Fetch all image files with thumbnails from database
    activity.heartbeat({"step": "fetch_images", "message": "Fetching image files from database"})
    
    def get_image_files_sync():
        with SessionLocal() as db:
            # Query for image files that have thumbnails
            image_mime_types = [
                "image/jpeg",   
                "image/png",
                "image/heic",
                "image/heif"
            ]

            
            return db.query(
                GoogleDriveFile.file_id,
                GoogleDriveFile.file_name,
                GoogleDriveFile.thumbnail_link,
                GoogleDriveFile.file_path,
                GoogleDriveFile.mime_type
            ).filter(
                GoogleDriveFile.user_id == user_id,
                GoogleDriveFile.google_drive_account_id == google_drive_account_id,
                GoogleDriveFile.mime_type.in_(image_mime_types),
                GoogleDriveFile.thumbnail_link.isnot(None)
            ).all()
    
    image_files = await loop.run_in_executor(None, get_image_files_sync)
    
    total_images = len(image_files)
    activity.heartbeat({
        "step": "fetch_images_complete",
        "message": f"Found {total_images} image files with thumbnails"
    })
    
    if total_images == 0:
        return {
            "message": "No images found to process",
            "total_processed": 0
        }
    
    # Step 2: Get ChromaDB collection for this user+account
    activity.heartbeat({"step": "init_chroma", "message": "Initializing ChromaDB collection"})
    
    def get_collection_sync():
        return get_image_captions_collection(user_id, google_drive_account_id)
    
    collection = await loop.run_in_executor(None, get_collection_sync)
    
    # Step 3: Process images in batches with rate limiting
    batch_size = 5  # Reduced batch size to respect API limits
    delay_between_images = 2  # Seconds to wait between each image (avoid rate limits)
    processed_count = 0
    failed_count = 0
    captions_to_save = []
    
    for i in range(0, total_images, batch_size):
        batch = image_files[i:i + batch_size]
        
        activity.heartbeat({
            "step": "processing_batch",
            "batch": i // batch_size + 1,
            "total_batches": (total_images + batch_size - 1) // batch_size,
            "processed": processed_count,
            "failed": failed_count
        })
        
        # Process each image in the batch
        for file in batch:
            try:
                file_id = file.file_id
                thumbnail_link = file.thumbnail_link
                file_name = file.file_name
                file_path = file.file_path
                mime_type = file.mime_type
                
                activity.heartbeat({
                    "step": "processing_image",
                    "file_name": file_name,
                    "processed": processed_count + 1,
                    "total": total_images
                })
                
                print(f"🔄 Processing: {file_name}")
                print(f"   Thumbnail: {thumbnail_link[:80]}...")
                
                # Check which captioning service to use (local model vs Gemini API)
                use_local_model = os.getenv("USE_LOCAL_VISION_MODEL", "false").lower() == "true"
                
                if use_local_model:
                    # Use local vision model (CPU-based)
                    print(f"   🤖 Using local vision model for captioning...")
                    
                    # Download FULL-RESOLUTION image (not thumbnail) for better caption quality
                    # Local models benefit from higher resolution images
                    image = await download_thumbnail(
                        thumbnail_link, 
                        access_token=access_token,
                        file_id=file_id,
                        prefer_full_image=True,  # Download full image instead of thumbnail
                        max_size=1024  # Resize to 1024px max (good balance between quality and memory)
                    )
                    
                    # Auto-detect which local model to use based on LOCAL_VISION_MODEL env var
                    model_name = os.getenv("LOCAL_VISION_MODEL", "").lower()
                    
                    if "blip" in model_name:
                        # Use BLIP model (fine-tuned or base, better quality)
                        print(f"   🎨 Using BLIP model for high-quality captions (model: {model_name})")
                        local_service = get_blip_caption_service()
                    else:
                        # Use ViT-GPT2 model (faster but lower quality)
                        print(f"   🤖 Using ViT-GPT2 model")
                        local_service = get_local_caption_service()
                    
                    # Run model inference in thread pool (blocking operation)
                    caption = await loop.run_in_executor(
                        None,
                        local_service.generate_caption,
                        image
                    )
                    
                    print(f"✅ Local caption generated: {caption[:100]}...")
                else:
                    # Use Gemini API (original behavior)
                    print(f"   🤖 Using Gemini API for captioning...")
                    
                    # Generate caption using Gemini (with authenticated thumbnail download and retries)
                    # Includes file_id for API fallback when thumbnail URL fails (403 errors)
                    caption = await generate_caption_from_url(
                        thumbnail_link, 
                        access_token=access_token,
                        file_id=file_id,  # For Drive API fallback
                        max_retries=3  # Will retry up to 3 times with exponential backoff
                    )
                    
                    print(f"✅ Gemini caption generated: {caption[:100]}...")
                
                activity.heartbeat({
                    "step": "caption_generated",
                    "file_name": file_name,
                    "processed": processed_count + 1,
                    "total": total_images
                })

                # Add delay between API calls to avoid rate limiting
                if processed_count + failed_count < total_images - 1:  # Don't delay after last image
                    print(f"   ⏳ Waiting {delay_between_images}s before next image (rate limit protection)...")
                    await asyncio.sleep(delay_between_images)

                # Generate unique ChromaDB document ID
                chroma_doc_id = f"{user_id}_{google_drive_account_id}_{file_id}"
                
                # Add to ChromaDB with automatic embedding
                def add_to_chroma_sync():
                    collection.add(
                        documents=[caption],
                        ids=[chroma_doc_id],
                        metadatas=[{
                            "file_id": file_id,
                            "file_name": file_name,
                            "file_path": file_path,
                            "mime_type": mime_type,
                            "user_id": user_id,
                            "google_drive_account_id": google_drive_account_id
                        }]
                    )
                
                await loop.run_in_executor(None, add_to_chroma_sync)

                activity.heartbeat({
                    "step": "chroma_saved",
                    "file_name": file_name,
                    "processed": processed_count + 1,
                    "total": total_images
                })

                # Prepare caption data for PostgreSQL
                captions_to_save.append({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "google_drive_account_id": google_drive_account_id,
                    "file_id": file_id,
                    "caption": caption,
                    "chroma_doc_id": chroma_doc_id,
                    "file_metadata": {
                        "file_name": file_name,
                        "file_path": file_path,
                        "mime_type": mime_type
                    }
                })
                
                processed_count += 1
                
            except Exception as e:
                failed_count += 1
                error_details = {
                    "step": "processing_error",
                    "file_name": file.file_name,
                    "file_id": file.file_id,
                    "thumbnail_link": file.thumbnail_link,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "failed": failed_count
                }
                activity.heartbeat(error_details)
                # Print to console for debugging
                print(f"❌ Error processing {file.file_name}: {type(e).__name__} - {str(e)}")
                print(f"   Thumbnail URL: {file.thumbnail_link}")
                # Continue processing other images even if one fails
                continue
        
        # Save batch of captions to database
        if captions_to_save:
            activity.heartbeat({
                "step": "saving_captions",
                "count": len(captions_to_save)
            })
            
            def save_captions_sync(captions_data):
                with SessionLocal() as db:
                    try:
                        stmt = insert(GoogleDriveImageCaption).values(captions_data)
                        upsert_stmt = stmt.on_conflict_do_update(
                            index_elements=["file_id"],
                            set_={
                                "caption": stmt.excluded.caption,
                                "chroma_doc_id": stmt.excluded.chroma_doc_id,
                                "file_metadata": stmt.excluded.file_metadata,
                                "updated_at": datetime.now(timezone.utc)
                            }
                        )
                        db.execute(upsert_stmt)
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        raise e
            
            await loop.run_in_executor(None, partial(save_captions_sync, captions_to_save))
            captions_to_save = []  # Clear batch
    
    activity.heartbeat({
        "step": "complete",
        "message": "Image RAG pipeline completed",
        "processed": processed_count,
        "failed": failed_count
    })
    
    return {
        "message": "Image RAG pipeline completed successfully",
        "total_images": total_images,
        "processed": processed_count,
        "failed": failed_count,
        "success_rate": f"{(processed_count / total_images * 100):.2f}%" if total_images > 0 else "0%"
    }
