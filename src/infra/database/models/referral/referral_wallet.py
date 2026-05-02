"""Referral wallet model — tracks user balance and lifetime payout totals."""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.database.config import Base


class ReferralWallet(Base):
    __tablename__ = "referral_wallets"

    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    balance = Column(Integer, nullable=False, default=0)
    total_earned = Column(Integer, nullable=False, default=0)
    total_revoked = Column(Integer, nullable=False, default=0)
    total_withdrawn = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="referral_wallet")
