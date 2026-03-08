import uuid
import enum
from sqlalchemy import Column, String, Integer, Boolean, Numeric, DateTime, JSON, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base


class SubscriptionCycle(enum.Enum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionTier(enum.Enum):
    FREE = "FREE"
    BASE = "BASE"
    PRO = "PRO"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    uuid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    package_name = Column(String, nullable=False)

    monthly_price = Column(Numeric, nullable=True)
    yearly_price = Column(Numeric, nullable=True)

    no_of_accounts = Column(Integer, nullable=False)
    no_of_email_accounts = Column(Integer, nullable=True)
    no_of_cloud_accounts = Column(Integer, nullable=True)
    no_of_social_accounts = Column(Integer, nullable=True)

    max_connected_drives = Column(Integer, nullable=False)
    tier = Column(Enum(SubscriptionTier, name="SubscriptionTier", create_constraint=False, native_enum=True), nullable=False)
    action_limit = Column(Boolean, nullable=False)
    cycle = Column(Enum(SubscriptionCycle, name="SubscriptionCycle", create_constraint=False, native_enum=True), nullable=False)

    features = Column(JSON, nullable=False)
    description = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    subscribed_users = relationship("SubscribedUser", back_populates="subscription_plan")
