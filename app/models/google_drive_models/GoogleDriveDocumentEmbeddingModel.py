import uuid
from sqlalchemy import Column, String, ForeignKey, Text, DateTime, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class GoogleDriveDocumentEmbedding(Base):
    __tablename__ = "google_drive_document_embeddings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    google_drive_account_id = Column(String, ForeignKey("google_drive_accounts.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String, ForeignKey("google_drive_files.file_id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Extracted text content (truncated for storage)
    text_content = Column(Text, nullable=False)
    
    # Text summary/preview
    text_preview = Column(Text, nullable=True)
    
    # ChromaDB document ID for vector retrieval
    chroma_doc_id = Column(String, nullable=False, unique=True)
    
    # Document extraction metadata
    extraction_metadata = Column(JSON, nullable=True)
    
    # Content statistics
    word_count = Column(Integer, nullable=True)
    char_count = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    file = relationship("GoogleDriveFile", foreign_keys=[file_id])
