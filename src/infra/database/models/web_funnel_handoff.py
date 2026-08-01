"""Durable state for RevenueCat-first web funnel claims."""

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.infra.database.base import Base
from src.infra.database.models.base import BaseMixin


class WebFunnelLead(Base, BaseMixin):
    """An unverified checkout email bound to an opaque RevenueCat App User ID."""

    __tablename__ = "web_funnel_leads"

    normalized_email = Column(String(254), nullable=False, index=True)
    draft_access_key_hash = Column(String(64), nullable=False)
    source = Column(String(64), nullable=False)
    source_revision = Column(String(32), nullable=False)
    onboarding_payload = Column(JSON, nullable=True)
    plan_snapshot = Column(JSON, nullable=True)
    state = Column(String(32), nullable=False, index=True, default="draft")
    revenuecat_app_user_id = Column(String(64), nullable=False, unique=True)
    revenuecat_transaction_id = Column(String(255), nullable=True, unique=True)
    revenuecat_store = Column(String(32), nullable=True)
    payment_verified_at = Column(DateTime(timezone=True), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    # The claim is locally durable before RevenueCat receipt association finishes.
    # This is deliberately an access-sync projection, not a second entitlement.
    access_sync_status = Column(String(16), nullable=False, default="pending")

    claims = relationship(
        "WebFunnelClaim", back_populates="lead", cascade="all, delete-orphan", lazy="raise"
    )

    __table_args__ = (
        Index("idx_web_funnel_lead_draft_access", "normalized_email", "draft_access_key_hash"),
    )


class WebFunnelClaim(Base, BaseMixin):
    """Single-use capability used only after Firebase authentication."""

    __tablename__ = "web_funnel_claims"

    lead_id = Column(String(36), ForeignKey("web_funnel_leads.id", ondelete="CASCADE"), nullable=False)
    generation = Column(Integer, nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    status = Column(String(32), nullable=False, default="active")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    claimed_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    lead = relationship("WebFunnelLead", back_populates="claims", lazy="raise")

    __table_args__ = (
        UniqueConstraint("lead_id", "generation", name="uq_web_funnel_claim_generation"),
        Index("idx_web_funnel_claim_status_expiry", "status", "expires_at"),
    )
