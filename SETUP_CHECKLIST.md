# RAG Pipeline Setup Checklist

Use this checklist to ensure your RAG pipeline is properly configured and running.

## ✅ Pre-Installation Checklist

- [ ] Python 3.8+ installed
- [ ] PostgreSQL database running
- [ ] Temporal server running (localhost:7233)
- [ ] Access to Google AI Studio for Gemini API key
- [ ] Git repository cloned

## ✅ Installation Steps

### 1. Environment Setup
- [ ] Create/verify `.env` file exists
- [ ] Add `GEMINI_API_KEY=your_key_here` to `.env`
- [ ] Add `CHROMA_DB_PATH=./chroma_db` to `.env` (optional)
- [ ] Verify existing environment variables:
  - [ ] `DATABASE_LINK`
  - [ ] `TEMPORAL_CLIENT`
  - [ ] `GOOGLE_CLIENT_ID`
  - [ ] `GOOGLE_CLIENT_SECRET`

### 2. Get Gemini API Key
- [ ] Visit https://makersuite.google.com/app/apikey
- [ ] Create a new API key
- [ ] Copy key to `.env` file
- [ ] Test key validity (will verify in testing step)

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
- [ ] Run command successfully
- [ ] No error messages
- [ ] Verify new packages installed:
  - [ ] google-generativeai
  - [ ] chromadb
  - [ ] sentence-transformers
  - [ ] Pillow
  - [ ] httpx

### 4. Database Migration
```bash
alembic upgrade head
```
- [ ] Run migration command
- [ ] No errors during migration
- [ ] Verify `google_drive_image_captions` table created:
  ```sql
  SELECT * FROM google_drive_image_captions LIMIT 1;
  ```

### 5. Run Tests
```bash
python test_rag_pipeline.py
```
- [ ] All environment variables detected
- [ ] PostgreSQL connection successful
- [ ] Gemini API connection successful
- [ ] ChromaDB initialization successful
- [ ] Image download test passed
- [ ] All tests show ✅ PASSED

## ✅ Running the System

### 1. Start Temporal Workers
```bash
python app/temporal/google_drive/workers/GoogleDriveMetaDataWorker.py
```
- [ ] Command runs without errors
- [ ] Console shows "Worker started"
- [ ] Four workers initialized:
  - [ ] folders-task-queue
  - [ ] files-task-queue
  - [ ] rag-task-queue (NEW)
  - [ ] one-drive-metadata-task-queue

### 2. Start API Server
```bash
python main.py
```
- [ ] Server starts on port 8001
- [ ] No import errors
- [ ] API docs accessible at http://localhost:8001/docs
- [ ] New endpoints visible:
  - [ ] `/api/image-search/search`
  - [ ] `/api/image-search/caption/{file_id}`
  - [ ] `/api/image-search/captions/list`

### 3. Verify Temporal UI
- [ ] Open http://localhost:8233
- [ ] Temporal UI loads
- [ ] Task queues visible
- [ ] No error messages

## ✅ Testing the Pipeline

### 1. Trigger Metadata Fetch
```bash
POST /authenticated/google-drive/fetch-metadata
{
  "user_id": "your_user_id",
  "google_drive_account_id": "your_account_id"
}
```
- [ ] Request succeeds (200 status)
- [ ] Workflow ID returned
- [ ] Visible in Temporal UI

### 2. Monitor Processing
- [ ] Open workflow in Temporal UI
- [ ] Watch activities progress:
  - [ ] fetch_drive_folders completes
  - [ ] get_all_files_from_folders completes
  - [ ] process_images_for_rag starts (NEW)
- [ ] Monitor heartbeats in activity details
- [ ] Wait for completion (time varies by image count)

### 3. Verify Data Storage

#### PostgreSQL
```sql
-- Check captions created
SELECT COUNT(*) FROM google_drive_image_captions;

-- View sample captions
SELECT file_id, caption, created_at 
FROM google_drive_image_captions 
ORDER BY created_at DESC 
LIMIT 5;
```
- [ ] Records exist in database
- [ ] Captions are meaningful
- [ ] Timestamps are recent

#### ChromaDB
- [ ] Check `./chroma_db` directory exists
- [ ] Directory contains data files
- [ ] Size is reasonable (~1.5KB per image)

### 4. Test Search
```bash
POST /api/image-search/search
{
  "user_id": "your_user_id",
  "google_drive_account_id": "your_account_id",
  "query": "sunset beach photos",
  "limit": 10
}
```
- [ ] Request succeeds (200 status)
- [ ] Results returned
- [ ] Results have relevance scores
- [ ] Captions are included
- [ ] File details are complete

### 5. Try Multiple Queries
Test with various queries to verify semantic search:
- [ ] "photos of nature" - returns landscape images
- [ ] "documents with charts" - returns business documents
- [ ] "pictures of people" - returns photos with people
- [ ] "screenshots with code" - returns programming screenshots
- [ ] Custom query relevant to your data

## ✅ Performance Verification

### Processing Performance
- [ ] Check processing time in Temporal UI
- [ ] Typical: 2-3 seconds per image
- [ ] No timeouts or failures
- [ ] Success rate > 95%

### Search Performance
- [ ] Search completes in < 1 second
- [ ] Results are relevant
- [ ] Ranking makes sense

### Resource Usage
- [ ] Check disk space for ChromaDB
- [ ] Monitor PostgreSQL size
- [ ] Worker process not using excessive memory
- [ ] API server responsive

## ✅ Common Issues - Troubleshooting

### No Search Results
- [ ] Verify images have thumbnails in Google Drive
- [ ] Check RAG activity completed successfully
- [ ] Confirm ChromaDB collection exists
- [ ] Query `google_drive_image_captions` table

### Gemini API Errors
- [ ] Verify `GEMINI_API_KEY` in `.env`
- [ ] Check API key is valid
- [ ] Verify not hitting rate limits (15 req/min free tier)
- [ ] Check worker logs for specific errors

### ChromaDB Issues
- [ ] Verify `CHROMA_DB_PATH` is writable
- [ ] Check disk space available
- [ ] Try deleting and recreating: `rm -rf ./chroma_db`

### Worker Not Processing
- [ ] Verify Temporal server is running
- [ ] Check worker console for errors
- [ ] Verify all task queues initialized
- [ ] Check Temporal UI for workflow status

### Slow Processing
- [ ] Normal for large image collections
- [ ] Check network connection to Google Drive API
- [ ] Verify Gemini API responding quickly
- [ ] Consider adjusting batch size in code

## ✅ Production Readiness

### Security
- [ ] API keys in `.env` (not in code)
- [ ] `.env` added to `.gitignore`
- [ ] Database credentials secure
- [ ] HTTPS enabled (for production deployment)

### Monitoring
- [ ] Set up logging for workers
- [ ] Monitor Temporal UI regularly
- [ ] Set up alerts for workflow failures
- [ ] Track Gemini API quota usage

### Backup
- [ ] PostgreSQL backup strategy in place
- [ ] ChromaDB directory backed up
- [ ] `.env` file backed up securely

### Documentation
- [ ] Team trained on system
- [ ] Setup docs available (this checklist)
- [ ] Architecture documented (RAG_ARCHITECTURE.md)
- [ ] API endpoints documented (RAG_SETUP.md)

## ✅ Optional Enhancements

Consider these for advanced use cases:
- [ ] Set up monitoring dashboard
- [ ] Implement caching for frequent queries
- [ ] Add user feedback for caption quality
- [ ] Implement batch re-captioning
- [ ] Add document OCR support
- [ ] Set up distributed workers for scale

## 📊 Success Metrics

Your RAG pipeline is working correctly if:
- ✅ All tests pass
- ✅ Workers running without errors
- ✅ Images processed successfully (>95% success rate)
- ✅ Search returns relevant results
- ✅ Performance meets expectations (<3s per image, <1s per search)
- ✅ No frequent errors in logs

## 🎉 Completion

Once all items are checked:
- ✅ System is production-ready
- ✅ RAG pipeline fully functional
- ✅ Semantic search operational
- ✅ Team can use the system

---

## Quick Reference

### Start Everything
```bash
# Terminal 1 - Temporal Workers
python app/temporal/google_drive/workers/GoogleDriveMetaDataWorker.py

# Terminal 2 - API Server
python main.py
```

### Test Pipeline
```bash
python test_rag_pipeline.py
```

### Useful URLs
- API Docs: http://localhost:8001/docs
- Temporal UI: http://localhost:8233
- Gemini API Keys: https://makersuite.google.com/app/apikey

### Key Files
- Configuration: `.env`
- Tests: `test_rag_pipeline.py`
- Setup Guide: `RAG_SETUP.md`
- Quick Start: `QUICK_START_RAG.md`
- Architecture: `RAG_ARCHITECTURE.md`

---

**Last Updated**: 2026-02-03  
**Version**: 1.0.0  
**Status**: Complete ✅
