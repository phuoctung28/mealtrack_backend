"""PromoCode model — system-generated codes for email marketing campaigns."""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index, text
from sqlalchemy.orm import relationship

from src.infra.database.base import Base
from src.infra.database.models.base import PrimaryEntityMixin


class PromoCode(Base, PrimaryEntityMixin):
    __tablename__ = "promo_codes"

    code = Column(String(50), nullable=False)
    max_uses = Column(Integer, nullable=False)
    current_uses = Column(Integer, nullable=False, default=0, server_default=text('0'))
    is_active = Column(Boolean, nullable=False, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    description = Column(String(255), nullable=True)
    rc_offering_id = Column(String(50), nullable=False, default="email")

    __table_args__ = (
        Index("ix_promo_codes_code", "code", unique=True),
    )

    redemptions = relationship("PromoCodeRedemption", back_populates="promo_code", lazy="raise")
