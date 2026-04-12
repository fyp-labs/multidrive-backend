# Quick Start Guide - Image RAG Pipeline

## Prerequisites
1. Python 3.8+
2. PostgreSQL database running
3. Temporal server running (localhost:7233)
4. Gemini API key from Google AI Studio

## Step-by-Step Setup

### 1. Get Gemini API Key
```bash
# Visit: https://makersuite.google.com/app/apikey
# Create a new API key and copy it
```

### 2. Configure Environment
Add to your `.env` file:
```bash
GEMINI_API_KEY=your_api_key_here
CHROMA_DB_PATH=./chroma_db
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Database Migration
```bash
alembic upgrade head
```

### 5. Start Workers
```bash
python app/temporal/google_drive/workers/GoogleDriveMetaDataWorker.py
```

### 6. Start API Server
```bash
python main.py
```

## Testing the Pipeline

### 1. Trigger Metadata Fetch
This will automatically run the RAG pipeline after completing:
```bash
POST /authenticated/google-drive/fetch-metadata
{
  "user_id": "your_user_id",
  "google_drive_account_id": "your_account_id"
}
```

### 2. Wait for Processing
Monitor in Temporal UI: http://localhost:8233

### 3. Search Images
```bash
POST /api/image-search/search
{
  "user_id": "your_user_id",
  "google_drive_account_id": "your_account_id",
  "query": "photos of nature",
  "limit": 10
}
```

## Example Queries

Try these natural language queries:
- "sunset beach photos"
- "documents with charts"
- "pictures of people smiling"
- "screenshots with code"
- "food photos"
- "landscape images with mountains"

## What Gets Processed?

The pipeline automatically processes:
- ✅ All image files (JPEG, PNG, GIF, WebP, BMP, SVG)
- ✅ Files with available thumbnails
- ✅ From the authenticated user's Google Drive

## Monitoring

Check processing status:
1. **Temporal UI**: http://localhost:8233
2. **Worker Logs**: Console output shows progress
3. **Database**: Query `google_drive_image_captions` table

## Troubleshooting

### No results found?
- Ensure images have thumbnails in Google Drive
- Check if RAG activity completed successfully in Temporal
- Verify ChromaDB collection exists: check `./chroma_db` folder

### API errors?
- Verify `GEMINI_API_KEY` is set correctly
- Check API quota limits (15 requests/min on free tier)
- Review worker logs for errors

### Slow processing?
- Normal: 2-3 seconds per image
- Large collections take time (100 images ≈ 3-5 minutes)
- Consider running during off-peak hours

## Architecture Summary

```
User → API → Temporal Workflow → Activities:
  1. Fetch Folders
  2. Fetch Files
  3. Process Images (RAG) → Gemini + ChromaDB
    
Search → ChromaDB (vectors) + PostgreSQL (metadata) → Results
```

## Files Created

- `google_drive_image_captions` table in PostgreSQL
- `chroma_db/` folder with vector embeddings
- One collection per user+account in ChromaDB

## Support

For detailed information, see `RAG_SETUP.md`
