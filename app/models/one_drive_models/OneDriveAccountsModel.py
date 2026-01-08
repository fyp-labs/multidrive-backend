import uuid
from sqlalchemy import Column, String, ForeignKey, Integer, Text, JSON, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base


class OneDriveAccount(Base):
    __tablename__ = "one_drive_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    onedrive_account = Column(String, unique=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_in = Column(DateTime(timezone=True), nullable=False)
    scope = Column(Text, nullable=False)
    delta_link = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    folder_tree = relationship("OneDriveFolderTree", back_populates="account", uselist=False)
    folders = relationship("OneDriveFolder", back_populates="account")
    files = relationship("OneDriveFile", back_populates="account")
