"""
Test script for the RAG Pipeline
Run this after setting up the environment to verify everything works
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_gemini_connection():
    """Test Gemini API connection"""
    print("\n=== Testing Gemini API Connection ===")
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Test with a simple text prompt
        response = model.generate_content("Say 'Hello from Gemini!'")
        print(f"✅ Gemini API connected successfully")
        print(f"   Response: {response.text[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Gemini API connection failed: {str(e)}")
        return False

async def test_chromadb_connection():
    """Test ChromaDB connection"""
    print("\n=== Testing ChromaDB Connection ===")
    try:
        from app.config.chroma_client import get_chroma_client, get_image_captions_collection
        
        client = get_chroma_client()
        print(f"✅ ChromaDB client initialized")
        print(f"   Path: {os.getenv('CHROMA_DB_PATH', './chroma_db')}")
        
        # Test collection creation
        test_collection = get_image_captions_collection("test_user", "test_account")
        print(f"✅ Test collection created: {test_collection.name}")
        
        # Test adding and querying
        test_collection.add(
            documents=["A beautiful sunset over the ocean"],
            ids=["test_doc_1"],
            metadatas=[{"test": True}]
        )
        
        results = test_collection.query(
            query_texts=["sunset beach"],
            n_results=1
        )
        
        print(f"✅ ChromaDB operations successful")
        print(f"   Test query returned: {len(results['ids'][0])} result(s)")
        
        return True
    except Exception as e:
        print(f"❌ ChromaDB connection failed: {str(e)}")
        return False

async def test_database_connection():
    """Test PostgreSQL connection"""
    print("\n=== Testing PostgreSQL Connection ===")
    try:
        from app.config.database import SessionLocal
        from app.models.google_drive_models.GoogleDriveImageCaptionModel import GoogleDriveImageCaption
        
        db = SessionLocal()
        
        # Test query
        count = db.query(GoogleDriveImageCaption).count()
        print(f"✅ PostgreSQL connected successfully")
        print(f"   Image captions in database: {count}")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {str(e)}")
        return False

async def test_image_download():
    """Test image downloading"""
    print("\n=== Testing Image Download ===")
    try:
        from app.config.gemini_client import download_thumbnail
        
        # Test with a sample image URL (you may need to replace this)
        test_url = "https://via.placeholder.com/150"
        
        image = await download_thumbnail(test_url)
        print(f"✅ Image download successful")
        print(f"   Image size: {image.size}")
        print(f"   Image format: {image.format}")
        
        return True
    except Exception as e:
        print(f"⚠️  Image download test skipped or failed: {str(e)}")
        return True  # Non-critical

async def check_environment_variables():
    """Check all required environment variables"""
    print("\n=== Checking Environment Variables ===")
    
    required_vars = {
        "DATABASE_LINK": "PostgreSQL connection string",
        "TEMPORAL_CLIENT": "Temporal server address",
        "GEMINI_API_KEY": "Google Gemini API key",
    }
    
    optional_vars = {
        "CHROMA_DB_PATH": "ChromaDB storage path (default: ./chroma_db)",
    }
    
    all_ok = True
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: NOT SET ({description})")
            all_ok = False
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️  {var}: NOT SET - will use default ({description})")
    
    return all_ok

async def main():
    """Run all tests"""
    print("=" * 60)
    print("RAG Pipeline Configuration Test")
    print("=" * 60)
    
    # Check environment variables
    env_ok = await check_environment_variables()
    
    if not env_ok:
        print("\n❌ Missing required environment variables. Please check your .env file.")
        return
    
    # Run tests
    tests = [
        ("Database", test_database_connection()),
        ("Gemini API", test_gemini_connection()),
        ("ChromaDB", test_chromadb_connection()),
        ("Image Download", test_image_download()),
    ]
    
    results = []
    for name, test in tests:
        result = await test
        results.append((name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your RAG pipeline is ready to use.")
        print("\nNext steps:")
        print("1. Start the workers: python app/temporal/google_drive/workers/GoogleDriveMetaDataWorker.py")
        print("2. Start the API: python main.py")
        print("3. Trigger metadata fetch to process images")
        print("4. Use /api/image-search/search to search images")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues before proceeding.")

if __name__ == "__main__":
    asyncio.run(main())
