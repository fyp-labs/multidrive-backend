import uuid
from sqlalchemy import Column, String, ForeignKey, Integer, Text, JSON, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class GoogleDriveAccount(Base):
    __tablename__ = "google_drive_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    gmail_account = Column(String, unique=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_in = Column(BigInteger, nullable=False)
    scope = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    folders = relationship("GoogleDriveFolder", back_populates="account")
    files = relationship("GoogleDriveFile", back_populates="account")
    folder_tree = relationship("GoogleDriveFolderTree", back_populates="account", uselist=False)
