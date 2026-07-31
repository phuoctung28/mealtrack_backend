"""
Subscription model for tracking user subscriptions.
"""

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.base import Base
from src.infra.database.models.base import BaseMixin


class Subscription(Base, BaseMixin):
    """Stores provider-specific subscription records for a user."""

    __tablename__ = "subscriptions"

    # User relationship
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    # Provider identifiers. RevenueCat rows keep revenuecat_subscriber_id;
    # Paddle rows use the provider-specific IDs below.
    provider = Column(String(32), nullable=False, default="revenuecat")
    revenuecat_subscriber_id = Column(String(255), nullable=True, index=True)
    provider_customer_id = Column(String(64), nullable=True)
    provider_subscription_id = Column(String(64), nullable=True, unique=True)
    price_id = Column(String(64), nullable=True)
    product_id = Column(
        String(255), nullable=False
    )  # "premium_monthly" or "premium_yearly"
    platform = Column(Enum("ios", "android", "web", native_enum=False), nullable=False)

    # Subscription status
    status = Column(
        Enum(
            "active",
            "expired",
            "cancelled",
            "billing_issue",
            "refunded",
            "trialing",
            "paused",
            "past_due",
            "canceled",
            native_enum=False,
        ),
        nullable=False,
        default="active",
    )
    purchased_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Store metadata
    store_transaction_id = Column(String(255), nullable=True)
    is_sandbox = Column(Boolean, default=False, nullable=False)
    scheduled_change_action = Column(String(64), nullable=True)
    scheduled_change_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    # Indexes
    __table_args__ = (
        Index("idx_user_id_status", "user_id", "status"),
        Index("idx_expires_at", "expires_at"),
        Index("idx_revenuecat_subscriber_id", "revenuecat_subscriber_id"),
        Index(
            "idx_subscriptions_provider_customer", "provider", "provider_customer_id"
        ),
        Index(
            "idx_subscriptions_provider_user_status", "provider", "user_id", "status"
        ),
    )

    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        access_statuses = (
            {"active", "trialing"} if self.provider == "paddle" else {"active"}
        )
        if self.status not in access_statuses:
            return False
        if self.expires_at and utc_now() > self.expires_at:
            return False
        return True

    def is_monthly(self) -> bool:
        """Check if this is a monthly subscription."""
        return "monthly" in self.product_id.lower()

    def is_yearly(self) -> bool:
        """Check if this is a yearly subscription."""
        return (
            "yearly" in self.product_id.lower() or "annual" in self.product_id.lower()
        )
