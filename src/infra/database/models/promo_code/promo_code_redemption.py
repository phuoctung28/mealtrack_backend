"""PromoCodeRedemption model — one row per user+code redemption."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, UniqueConstraint

from src.infra.database.config import Base
from src.infra.database.models.base import PrimaryEntityMixin


class PromoCodeRedemption(Base, PrimaryEntityMixin):
    __tablename__ = "promo_code_redemptions"

    promo_code_id = Column(String(36), ForeignKey("promo_codes.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    redeemed_at = Column(DateTime(timezone=True), nullable=False)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("promo_code_id", "user_id", name="uq_promo_redemption_user"),
        Index("ix_promo_code_redemptions_promo_code_id", "promo_code_id"),
        Index("ix_promo_code_redemptions_user_id", "user_id"),
    )
