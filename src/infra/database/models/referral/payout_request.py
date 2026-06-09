"""Payout request model — user-initiated withdrawal requests for referral earnings."""

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import PrimaryEntityMixin


class PayoutRequest(Base, PrimaryEntityMixin):
    __tablename__ = "payout_requests"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    payment_method = Column(String(20), nullable=False)
    payment_details = Column(JSON, nullable=False)
    payment_account_type = Column(String(20), nullable=True)
    payment_account_masked = Column(String(64), nullable=True)
    payment_country = Column(String(2), nullable=True)
    payment_currency = Column(String(3), nullable=True)
    # status: pending | processing | completed | rejected
    status = Column(String(20), nullable=False, default="pending")
    admin_note = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_payout_requests_user_id", "user_id"),
        Index("idx_payout_requests_status_requested", "status", "requested_at"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'rejected')",
            name="check_payout_requests_status",
        ),
        CheckConstraint(
            "payment_method IN ('momo', 'bank')",
            name="check_payout_requests_payment_method",
        ),
    )

    user = relationship("User")
