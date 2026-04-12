# RAG Pipeline Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Multi-Drive Provider Backend                     │
│                              (FastAPI + Temporal)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
              ┌─────▼─────┐                      ┌─────▼─────┐
              │  FastAPI  │                      │ Temporal  │
              │   Server  │                      │  Workers  │
              └─────┬─────┘                      └─────┬─────┘
                    │                                  │
        ┌───────────┼──────────────────────────────────┤
        │           │                                  │
        ▼           ▼                                  ▼
┌──────────┐  ┌──────────┐                   ┌──────────────┐
│   API    │  │ Database │                   │   Temporal   │
│ Endpoints│  │PostgreSQL│                   │   Workflow   │
└──────────┘  └──────────┘                   └──────────────┘
```

## Data Flow - RAG Pipeline

### Phase 1: Metadata Collection
```
Google Drive API
       ↓
Fetch Folders Activity
       ↓
PostgreSQL (google_drive_folders)
       ↓
Fetch Files Activity
       ↓
PostgreSQL (google_drive_files)
```

### Phase 2: Image Processing (RAG Pipeline)
```
Query: SELECT images WITH thumbnails FROM google_drive_files
       ↓
┌──────────────────────────────────────────────┐
│   Process Images for RAG Activity            │
│   (Batch Processing: 10 images at a time)    │
└──────────────────────────────────────────────┘
       ↓
       ├─────────────────┐
       │                 │
       ▼                 ▼
[Download Thumbnail]   [Loop Each Image]
       ↓
       │
       ▼
┌─────────────────────┐
│   Gemini Vision API │
│  (Image Captioning) │
└─────────────────────┘
       │
       ▼
   [AI Caption]
       │
       ├────────────────┬────────────────┐
       │                │                │
       ▼                ▼                ▼
┌──────────────┐  ┌──────────┐  ┌─────────────────┐
│   ChromaDB   │  │PostgreSQL│  │  Caption Text   │
│  (Vectors)   │  │(Metadata)│  │ + File Metadata │
└──────────────┘  └──────────┘  └─────────────────┘
```

### Phase 3: Semantic Search
```
User Query: "sunset beach photos"
       ↓
┌─────────────────────────────────┐
│  Image Search Service           │
│  (ImageSearchService.py)        │
└─────────────────────────────────┘
       ↓
       ├───────────────┐
       │               │
       ▼               ▼
┌──────────────┐  ┌─────────────────┐
│   ChromaDB   │  │   Sentence      │
│   Query      │  │  Transformers   │
│              │  │  (Embedding)    │
└──────────────┘  └─────────────────┘
       │
       ▼
Vector Similarity Search
       │
       ▼
Top K Results (file_ids + distances)
       │
       ▼
┌──────────────────────────────────┐
│  PostgreSQL                      │
│  JOIN google_drive_files         │
│  + google_drive_image_captions   │
└──────────────────────────────────┘
       │
       ▼
Ranked Results with Details
       │
       ▼
   JSON Response
```

## Component Details

### 1. Database Layer (PostgreSQL)

#### Tables

**google_drive_files**
- Stores all file metadata from Google Drive
- Includes `thumbnail_link` for images
- Primary source for file information

**google_drive_image_captions**
- Stores AI-generated captions
- Links to files via `file_id`
- Contains `chroma_doc_id` for vector lookup
- Stores metadata for debugging

```sql
CREATE TABLE google_drive_image_captions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    google_drive_account_id VARCHAR NOT NULL,
    file_id VARCHAR NOT NULL UNIQUE,
    caption TEXT NOT NULL,
    chroma_doc_id VARCHAR NOT NULL UNIQUE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (file_id) REFERENCES google_drive_files(file_id)
);
```

### 2. Vector Store (ChromaDB)

**Collections**
- One collection per user+account: `gdrive_images_{user_id}_{account_id}`
- Automatic embedding generation using default model (all-MiniLM-L6-v2)
- Persistent storage in `./chroma_db`

**Document Structure**
```python
{
    "id": "user_account_fileid",
    "document": "AI generated caption text",
    "metadata": {
        "file_id": "google_drive_file_id",
        "file_name": "photo.jpg",
        "file_path": "My Drive/Photos/photo.jpg",
        "mime_type": "image/jpeg",
        "user_id": "user123",
        "google_drive_account_id": "account456"
    },
    "embedding": [0.123, -0.456, ...]  # 384-dimensional vector
}
```

### 3. AI Services

#### Gemini Vision API
- **Model**: gemini-1.5-flash
- **Purpose**: Generate descriptive captions from images
- **Input**: PIL Image object (downloaded thumbnail)
- **Output**: 2-3 sentence caption

**Caption Prompt**
```
Analyze this image and provide a detailed, descriptive caption.
Focus on:
- Main subjects and objects in the image
- Colors, composition, and visual style
- Context and setting
- Any text visible in the image
- Overall mood or theme

Keep the caption concise but informative (2-3 sentences).
```

#### Sentence Transformers
- **Model**: all-MiniLM-L6-v2 (default ChromaDB embedding)
- **Purpose**: Convert text captions to vector embeddings
- **Dimension**: 384
- **Speed**: ~10ms per embedding

### 4. Temporal Workflows

#### GoogleDriveMetaDataWorkflow
```python
1. Activity: fetch_drive_folders
   └─> Queue: folders-task-queue
   
2. Activity: get_all_files_from_folders
   └─> Queue: files-task-queue
   
3. Activity: process_images_for_rag [NEW]
   └─> Queue: rag-task-queue
   └─> Timeout: 2 hours
   └─> Heartbeat: 60 seconds
```

#### Activities Detail

**process_images_for_rag**
- Batch size: 10 images
- Error handling: Continue on failure
- Heartbeat monitoring: Per-image progress
- Retry policy: 2 attempts, 10s initial interval

### 5. API Endpoints

#### POST `/api/image-search/search`
Search images by natural language query

**Request**
```json
{
  "user_id": "string",
  "google_drive_account_id": "string",
  "query": "string",
  "limit": 10
}
```

**Response**
```json
{
  "success": true,
  "query": "sunset photos",
  "results_count": 5,
  "results": [
    {
      "file_id": "...",
      "file_name": "...",
      "file_path": "...",
      "caption": "...",
      "relevance_score": 0.89,
      "distance": 0.22,
      "thumbnail_link": "...",
      "web_view_link": "..."
    }
  ]
}
```

#### GET `/api/image-search/caption/{file_id}`
Get caption for specific file

#### POST `/api/image-search/captions/list`
List all captions with pagination

## Performance Characteristics

### Processing Speed
- **Caption Generation**: ~1-2 seconds per image
- **Embedding Creation**: ~10-50ms per caption
- **Database Insert**: ~5-10ms per record
- **Total per Image**: ~2-3 seconds

### Search Speed
- **Query Embedding**: ~10-50ms
- **Vector Search**: ~50-200ms (for 10K images)
- **DB Lookup**: ~10-50ms
- **Total Search Time**: <500ms typically

### Storage Requirements
- **PostgreSQL**: ~500 bytes per caption record
- **ChromaDB**: ~1.5 KB per embedding (384 dimensions)
- **Total per Image**: ~2 KB

### Scalability
- **10,000 images**: ~8-10 hours processing, <1s search
- **50,000 images**: ~40-50 hours processing, <2s search
- **100,000 images**: Consider distributed workers

## Error Handling

### Activity Level
```python
try:
    caption = await generate_caption(image)
    # Store in ChromaDB + PostgreSQL
    processed_count += 1
except Exception as e:
    failed_count += 1
    activity.heartbeat({"error": str(e)})
    continue  # Process next image
```

### Workflow Level
- Automatic retry with exponential backoff
- Maximum 2 attempts for expensive operations
- Failed images logged but don't stop pipeline

### API Level
- HTTP error codes (404, 500)
- Detailed error messages
- Graceful degradation

## Security Considerations

1. **API Keys**: Store in environment variables
2. **User Isolation**: Separate ChromaDB collections per user
3. **Database Access**: Foreign key constraints, cascade deletes
4. **Rate Limiting**: Consider for Gemini API calls
5. **Data Privacy**: Image thumbnails processed, not full images

## Monitoring & Observability

### Temporal UI
- Workflow execution status
- Activity heartbeats
- Error logs
- Retry attempts

### Application Logs
```python
activity.heartbeat({
    "step": "processing_image",
    "file_name": "photo.jpg",
    "processed": 15,
    "total": 100,
    "failed": 2
})
```

### Metrics to Monitor
- Processing rate (images/minute)
- Success rate (%)
- Gemini API quota usage
- ChromaDB collection size
- PostgreSQL table size
- Search latency

## Future Enhancements

### Short Term
1. Support for document OCR
2. Video thumbnail support
3. Batch re-captioning
4. Caption quality scoring

### Medium Term
1. Multi-modal search (image + text)
2. Caption refinement with user feedback
3. Clustering similar images
4. Duplicate detection

### Long Term
1. Custom embedding models
2. Distributed processing
3. Real-time updates
4. Advanced filtering (date, size, type)

## Dependencies

### Python Packages
```
google-generativeai==0.8.3    # Gemini API
chromadb==0.5.23              # Vector database
sentence-transformers==3.3.1   # Embedding models
Pillow==11.0.0                # Image processing
httpx==0.28.1                 # Async HTTP client
temporalio==1.18.0            # Workflow orchestration
fastapi==0.117.1              # Web framework
```

### External Services
- Google Gemini API (AI captions)
- Google Drive API (file access)
- Temporal Server (workflow engine)
- PostgreSQL Database (metadata)

## Configuration

### Environment Variables
```bash
GEMINI_API_KEY=<your_key>          # Required
CHROMA_DB_PATH=./chroma_db         # Optional, default shown
DATABASE_LINK=postgresql://...     # Required
TEMPORAL_CLIENT=localhost:7233     # Required
```

### Adjustable Parameters

**In Activity (GoogleDriveImageRAGActivity.py)**
```python
batch_size = 10              # Images per batch
model_name = "gemini-1.5-flash"  # Gemini model
```

**In Workflow (GoogleDriveMetaDataWorkflow.py)**
```python
start_to_close_timeout=timedelta(hours=2)   # Activity timeout
heartbeat_timeout=timedelta(seconds=60)     # Heartbeat interval
maximum_attempts=2                          # Retry attempts
```

**In ChromaDB Config (chroma_client.py)**
```python
collection_name_format = "gdrive_images_{user_id}_{account_id}"
```

## Testing

Run the test suite:
```bash
python test_rag_pipeline.py
```

Tests verify:
- ✅ Gemini API connection
- ✅ ChromaDB initialization
- ✅ PostgreSQL connection
- ✅ Image download capability
- ✅ Environment configuration

## Deployment Checklist

- [ ] PostgreSQL database running
- [ ] Temporal server running
- [ ] Environment variables configured
- [ ] Dependencies installed
- [ ] Database migrations applied
- [ ] Workers started
- [ ] API server started
- [ ] Test script passed
- [ ] Gemini API quota verified
- [ ] Storage space available (for ChromaDB)

---

**Version**: 1.0.0  
**Last Updated**: 2026-02-03  
**Maintained By**: Multi-Drive Provider Team
