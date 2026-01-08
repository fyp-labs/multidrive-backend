import uuid
from sqlalchemy import Column, String, ForeignKey, Integer, Text, JSON, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class OneDriveFolderTree(Base):
    __tablename__ = "one_drive_folders_trees"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    one_drive_account_id = Column(String, ForeignKey("one_drive_accounts.id", ondelete="CASCADE"), primary_key=True)

    folder_tree = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationship
    account = relationship("OneDriveAccount", back_populates="folder_tree")
