"""Referral code model — one unique invite code per user."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.infra.database.config import Base


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    code = Column(String(6), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_referral_codes_code", "code", unique=True),)

    user = relationship("User", back_populates="referral_code")
