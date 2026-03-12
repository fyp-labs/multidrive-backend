import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Integer, Text, JSON, DateTime, BigInteger, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=True)
    email_verified = Column(DateTime(timezone=True), nullable=True)
    role = Column(Enum(Role, name="role"), nullable=False, default=Role.USER, server_default="USER")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())