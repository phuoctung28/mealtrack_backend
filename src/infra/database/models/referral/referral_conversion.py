"""Referral conversion model — tracks each referred user and their commission status."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import PrimaryEntityMixin


class ReferralConversion(Base, PrimaryEntityMixin):
    __tablename__ = "referral_conversions"

    referrer_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    referred_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    code_used = Column(String(6), nullable=False)
    # status: pending | converted | revoked
    status = Column(String(20), nullable=False, default="pending")
    discount_applied = Column(Integer, nullable=True)
    commission_amount = Column(Integer, nullable=False, default=50000)
    trial_started_at = Column(DateTime(timezone=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_referral_conversions_referrer", "referrer_user_id"),
        Index("ix_referral_conversions_referred", "referred_user_id", unique=True),
    )

    referrer = relationship("User", foreign_keys=[referrer_user_id])
    referred = relationship("User", foreign_keys=[referred_user_id])
