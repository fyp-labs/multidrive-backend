import uuid
from sqlalchemy import Column, String, ForeignKey, Integer, Text, JSON, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class OneDriveFolder(Base):
    __tablename__ = "one_drive_folders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # Laravel column: uuid
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    one_drive_account_id = Column(String, ForeignKey("one_drive_accounts.id", ondelete="CASCADE"), nullable=False)

    folder_name = Column(String, nullable=False)
    folder_parents = Column(String, nullable=False)
    folder_path = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    account = relationship("OneDriveAccount", back_populates="folders")
    files = relationship("OneDriveFile", back_populates="folder")
