from sqlalchemy import Column, String, ForeignKey, Integer, Text, JSON, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class GoogleDriveFolder(Base):
    __tablename__ = "google_drive_folders"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    google_drive_account_id = Column(String, ForeignKey("google_drive_accounts.id", ondelete="CASCADE"), nullable=False)
    folder_name = Column(String, nullable=False)
    folder_parents = Column(String, nullable=False)
    folder_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    account = relationship("GoogleDriveAccount", back_populates="folders")