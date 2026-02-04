# Google Drive Image RAG Pipeline Setup Guide

This document describes the RAG (Retrieval-Augmented Generation) pipeline for image captioning and semantic search in the Google Drive section.

## Overview

The RAG pipeline automatically:
1. **Downloads image thumbnails** from Google Drive after metadata fetching completes
2. **Generates captions** using Google's Gemini Vision API
3. **Creates vector embeddings** from the captions using sentence transformers
4. **Stores embeddings** in ChromaDB for fast semantic search
5. **Saves caption metadata** in PostgreSQL for reference

## Architecture

### Components

1. **Database Models**
   - `GoogleDriveImageCaptionModel.py` - Stores caption metadata in PostgreSQL

2. **Configuration**
   - `chroma_client.py` - ChromaDB client for vector storage
   - `gemini_client.py` - Gemini API client for image captioning

3. **Temporal Activities**
   - `GoogleDriveImageRAGActivity.py` - Processes images through the RAG pipeline

4. **Workflow**
   - `GoogleDriveMetaDataWorkflow.py` - Extended to include RAG pipeline after file fetching

5. **Services & Controllers**
   - `ImageSearchService.py` - Semantic search functionality
   - `ImageSearchController.py` - API controllers for search endpoints

6. **API Routes**
   - `image_search_routes.py` - REST endpoints for image search

## Setup Instructions

### 1. Environment Variables

Add the following to your `.env` file:

```bash
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# ChromaDB Configuration
CHROMA_DB_PATH=./chroma_db

# Existing variables (ensure these are set)
DATABASE_LINK=postgresql://user:password@localhost/dbname
TEMPORAL_CLIENT=localhost:7233
```

### 2. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file as `GEMINI_API_KEY`

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `google-generativeai==0.8.3` - Gemini API client
- `chromadb==0.5.23` - Vector database
- `sentence-transformers==3.3.1` - Embedding models
- `Pillow==11.0.0` - Image processing
- `httpx==0.28.1` - Async HTTP client

### 4. Run Database Migration

```bash
alembic upgrade head
```

This creates the `google_drive_image_captions` table.

### 5. Start Workers

The RAG pipeline requires the workers to be running:

```bash
python app/temporal/google_drive/workers/GoogleDriveMetaDataWorker.py
```

This now includes:
- `folders-task-queue` - Folder fetching
- `files-task-queue` - File fetching
- `rag-task-queue` - **NEW** Image processing and captioning

### 6. Start the API Server

```bash
python main.py
```

## Usage

### Automatic Processing

When you trigger the Google Drive metadata workflow, it will automatically:
1. Fetch folders and files
2. **Process all images with thumbnails through the RAG pipeline**
3. Generate captions and embeddings

### API Endpoints

#### 1. Search Images by Text

**POST** `/api/image-search/search`

```json
{
  "user_id": "user123",
  "google_drive_account_id": "gdrive456",
  "query": "sunset beach photos",
  "limit": 10
}
```

**Response:**
```json
{
  "success": true,
  "query": "sunset beach photos",
  "results_count": 5,
  "results": [
    {
      "file_id": "abc123",
      "file_name": "beach_sunset.jpg",
      "file_path": "My Drive/Photos/beach_sunset.jpg",
      "mime_type": "image/jpeg",
      "file_size": 2048000,
      "thumbnail_link": "https://...",
      "web_view_link": "https://...",
      "caption": "A beautiful sunset over a beach with orange and pink clouds...",
      "relevance_score": 0.89,
      "distance": 0.22
    }
  ]
}
```

#### 2. Get Caption for Specific Image

**GET** `/api/image-search/caption/{file_id}`

Returns the AI-generated caption for a specific file.

#### 3. List All Captions

**POST** `/api/image-search/captions/list`

```json
{
  "user_id": "user123",
  "google_drive_account_id": "gdrive456",
  "skip": 0,
  "limit": 100
}
```

## How It Works

### RAG Pipeline Flow

```
Google Drive Files (with thumbnails)
          ↓
Download Thumbnail Images
          ↓
Gemini Vision API (Caption Generation)
          ↓
Sentence Transformers (Create Embeddings)
          ↓
ChromaDB (Store Vectors) + PostgreSQL (Store Captions)
          ↓
Semantic Search Available
```

### Search Process

```
User Query: "photos of cats"
          ↓
Convert Query to Embedding
          ↓
ChromaDB Similarity Search
          ↓
Retrieve Top K Results
          ↓
Fetch File Details from PostgreSQL
          ↓
Return Ranked Results
```

## Features

### Image Caption Generation
- Uses **Gemini 1.5 Flash** for fast, accurate image understanding
- Generates detailed 2-3 sentence captions
- Focuses on subjects, colors, context, and visible text

### Semantic Search
- Natural language queries
- Relevance scoring (0-1)
- Fast vector similarity search
- Isolated collections per user/account

### Performance Optimizations
- Batch processing (10 images at a time)
- Heartbeat monitoring for long-running tasks
- Error handling with per-image failure tracking
- Automatic retry with exponential backoff

## Data Storage

### PostgreSQL
Stores caption metadata in `google_drive_image_captions`:
- `file_id` - Links to Google Drive file
- `caption` - AI-generated text description
- `chroma_doc_id` - Links to ChromaDB vector
- `metadata` - Additional file information

### ChromaDB
Stores vector embeddings:
- Uses default embedding model (all-MiniLM-L6-v2)
- Persistent storage in `./chroma_db`
- Separate collections per user+account
- Automatic similarity search

## Monitoring

The RAG activity provides detailed heartbeats:
```json
{
  "step": "processing_image",
  "file_name": "photo.jpg",
  "processed": 15,
  "total": 100
}
```

Monitor progress in Temporal UI at `http://localhost:8233`

## Error Handling

- Individual image failures don't stop the pipeline
- Failed images are logged and counted
- Workflow continues processing remaining images
- Final report includes success rate

## Troubleshooting

### ChromaDB Issues
```bash
# Reset ChromaDB (deletes all embeddings)
rm -rf ./chroma_db
```

### Gemini API Rate Limits
- Free tier: 15 requests per minute
- Adjust batch size if hitting limits
- Consider upgrading to paid tier for production

### Missing Captions
- Check if images have `thumbnail_link` in database
- Verify Gemini API key is valid
- Check worker logs for errors

## Performance Considerations

- **Processing Time**: ~2-3 seconds per image (caption + embedding)
- **Storage**: ~1KB per caption in PostgreSQL, ~1KB per embedding in ChromaDB
- **Search Speed**: Sub-second for queries up to 10,000 images

## Future Enhancements

Potential improvements:
1. Support for document OCR and text extraction
2. Multi-modal search (text + image similarity)
3. Caption refinement with user feedback
4. Batch re-captioning on model updates
5. Support for video thumbnails

## License

Part of the Multi-Drive Provider project.
