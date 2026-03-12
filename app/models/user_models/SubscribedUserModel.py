import uuid
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base


class SubscribedUser(Base):
    __tablename__ = "subscribed_users"

    uuid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    subscription_plan_id = Column(String, ForeignKey("subscription_plans.uuid", ondelete="CASCADE"), nullable=False)
    connected_accounts = Column(Integer, nullable=False)
    connected_email_accounts = Column(Integer, nullable=False, default=0)
    connected_cloud_accounts = Column(Integer, nullable=False, default=0)
    connected_social_accounts = Column(Integer, nullable=False, default=0)
    usage = Column(Integer, nullable=False)
    paid_amount = Column(Numeric, nullable=True)
    sub_start_time = Column(DateTime(timezone=True), nullable=True)
    sub_end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="subscription")
    subscription_plan = relationship("SubscriptionPlan", back_populates="subscribed_users")
