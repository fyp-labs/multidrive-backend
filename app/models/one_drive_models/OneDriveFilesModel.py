import uuid
from sqlalchemy import Column, String, ForeignKey, Integer, Text, JSON, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class OneDriveFile(Base):
    __tablename__ = "one_drive_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    one_drive_account_id = Column(String, ForeignKey("one_drive_accounts.id", ondelete="CASCADE"), nullable=False)

    file_id = Column(String, unique=True, nullable=False)
    file_name = Column(String, nullable=False)

    file_parents = Column(String, ForeignKey("one_drive_folders.id", ondelete="CASCADE"), nullable=False)

    file_created_time = Column(DateTime(timezone=True), nullable=False)
    md5Checksum = Column(String, nullable=True)
    mimeType = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=True)
    file_path = Column(Text, nullable=False)
    last_modified_time = Column(DateTime, nullable=True)
    webViewLink = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    account = relationship("OneDriveAccount", back_populates="files")
    folder = relationship("OneDriveFolder", back_populates="files")
