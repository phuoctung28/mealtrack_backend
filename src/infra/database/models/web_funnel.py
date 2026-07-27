"""Web funnel checkout ledger models."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.infra.database.base import Base
from src.infra.database.models.base import BaseMixin


class WebFunnelLead(Base, BaseMixin):
    """Public lead identity used to correlate funnel checkout attempts."""

    __tablename__ = "web_funnel_leads"

    external_lead_id = Column(String(128), nullable=False, unique=True, index=True)
    email_hash = Column(String(64), nullable=True)
    first_seen_country = Column(String(2), nullable=True)
    last_seen_country = Column(String(2), nullable=True)

    checkouts = relationship("WebFunnelCheckout", back_populates="lead")


class WebFunnelCheckout(Base, BaseMixin):
    """Server-owned checkout state for a web funnel purchase."""

    __tablename__ = "web_funnel_checkouts"

    lead_id = Column(
        String(36),
        ForeignKey("web_funnel_leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key_hash = Column(String(64), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    state = Column(
        String(32),
        nullable=False,
        default="pending_approval",
        server_default="pending_approval",
    )
    state_reason = Column(String(255), nullable=True)

    offer_id = Column(String(64), nullable=False)
    reward_id = Column(String(64), nullable=False)
    market = Column(String(16), nullable=False)
    billing_country = Column(String(2), nullable=False)
    provider = Column(String(32), nullable=False)
    currency = Column(String(3), nullable=False)
    amount_minor = Column(Integer, nullable=False)
    renewal_interval = Column(String(16), nullable=False)
    welcome_discount_percent = Column(Integer, nullable=False, default=0)

    provider_plan_id = Column(String(255), nullable=True)
    provider_subscription_id = Column(String(255), nullable=True)
    provider_customer_id = Column(String(255), nullable=True)
    provider_transaction_id = Column(String(255), nullable=True)
    custom_id_hash = Column(String(64), nullable=False, unique=True)
    claim_token_hash = Column(String(64), nullable=False, unique=True)
    claim_expires_at = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)

    lead = relationship("WebFunnelLead", back_populates="checkouts")
    claims = relationship("WebFunnelClaim", back_populates="checkout")

    __table_args__ = (
        UniqueConstraint(
            "lead_id",
            "idempotency_key_hash",
            name="uq_web_funnel_checkout_lead_idempotency",
        ),
        UniqueConstraint(
            "provider",
            "provider_subscription_id",
            name="uq_web_funnel_checkout_provider_subscription",
        ),
        CheckConstraint("amount_minor >= 0", name="ck_web_funnel_amount_nonnegative"),
        Index("idx_web_funnel_checkouts_state", "state"),
        Index("idx_web_funnel_checkouts_lead_state", "lead_id", "state"),
    )


class WebFunnelProviderEvent(Base, BaseMixin):
    """Deduplicated billing-provider webhook event."""

    __tablename__ = "web_funnel_provider_events"

    provider = Column(String(32), nullable=False)
    event_id = Column(String(255), nullable=False)
    event_type = Column(String(128), nullable=False)
    provider_subscription_id = Column(String(255), nullable=True, index=True)
    checkout_id = Column(
        String(36),
        ForeignKey("web_funnel_checkouts.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified = Column(Boolean, nullable=False, default=False, server_default="false")
    processed = Column(Boolean, nullable=False, default=False, server_default="false")
    processing_result = Column(String(64), nullable=False, default="stored")
    safe_payload = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "provider", "event_id", name="uq_web_funnel_provider_event"
        ),
        Index("idx_web_funnel_provider_events_checkout", "checkout_id"),
    )


class WebFunnelClaim(Base, BaseMixin):
    """One-time claim binding from a paid checkout to an app user."""

    __tablename__ = "web_funnel_claims"

    checkout_id = Column(
        String(36),
        ForeignKey("web_funnel_checkouts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    claim_token_hash = Column(String(64), nullable=False, unique=True)
    claimed_at = Column(DateTime(timezone=True), nullable=False)

    checkout = relationship("WebFunnelCheckout", back_populates="claims")

    __table_args__ = (Index("idx_web_funnel_claims_user", "user_id"),)
