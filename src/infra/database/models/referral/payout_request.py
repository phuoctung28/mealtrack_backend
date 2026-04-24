"""Payout request model — user-initiated withdrawal requests for referral earnings."""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import PrimaryEntityMixin


class PayoutRequest(Base, PrimaryEntityMixin):
    __tablename__ = "payout_requests"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    payment_method = Column(String(20), nullable=False)
    payment_details = Column(JSON, nullable=False)
    # status: pending | processing | completed | rejected
    status = Column(String(20), nullable=False, default="pending")
    admin_note = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_payout_requests_user_id", "user_id"),
    )

    user = relationship("User")
