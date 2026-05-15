"""PromoCodeRedemption model — one row per user+code redemption."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import PrimaryEntityMixin
from src.domain.utils.timezone_utils import utc_now


class PromoCodeRedemption(Base, PrimaryEntityMixin):
    __tablename__ = "promo_code_redemptions"

    promo_code_id = Column(String(36), ForeignKey("promo_codes.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    redeemed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("promo_code_id", "user_id", name="uq_promo_redemption_user"),
        Index("ix_promo_code_redemptions_promo_code_id", "promo_code_id"),
        Index("ix_promo_code_redemptions_user_id", "user_id"),
    )

    promo_code = relationship("PromoCode", back_populates="redemptions")
    user = relationship("User", foreign_keys=[user_id])
    subscription = relationship("Subscription", foreign_keys=[subscription_id])
