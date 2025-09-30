import uuid
from sqlalchemy import Column, String, ForeignKey, Integer, Text, JSON, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class GoogleDriveFile(Base):
    __tablename__ = "google_drive_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    google_drive_account_id = Column(String, ForeignKey("google_drive_accounts.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String, unique=True, nullable=False)
    file_name = Column(String, nullable=False)

    file_parents = Column(String, ForeignKey("google_drive_folders.id", ondelete="CASCADE"), nullable=False)

    file_created_time = Column(DateTime, nullable=False)
    md5Checksum = Column(String, nullable=True)
    mime_type = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=True)
    viewed_by_me_time = Column(DateTime, nullable=True)
    file_path = Column(Text, nullable=False)
    web_view_link = Column(String, nullable=True)
    thumbnail_link = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    account = relationship("GoogleDriveAccount", back_populates="files")
