"""
Subscription model for tracking user subscriptions.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.base import Base
from src.infra.database.models.base import BaseMixin


class Subscription(Base, BaseMixin):
    """
    Stores subscription records synced from billing providers.

    RevenueCat remains the native-purchase source of truth. Claimed web
    checkouts create local provider-neutral rows after verified provider events.
    """

    __tablename__ = "subscriptions"

    # User relationship
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # RevenueCat data
    revenuecat_subscriber_id = Column(String(255), nullable=True, index=True)
    provider = Column(String(32), nullable=False, default="revenuecat")
    provider_customer_id = Column(String(255), nullable=True)
    provider_subscription_id = Column(String(255), nullable=True)
    provider_transaction_id = Column(String(255), nullable=True)
    source_checkout_id = Column(
        String(36),
        ForeignKey("web_funnel_checkouts.id", ondelete="SET NULL"),
        nullable=True,
    )
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

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    # Indexes
    __table_args__ = (
        Index("idx_user_id_status", "user_id", "status"),
        Index("idx_expires_at", "expires_at"),
        Index("idx_revenuecat_subscriber_id", "revenuecat_subscriber_id"),
        Index("idx_subscriptions_provider_user_status", "provider", "user_id", "status"),
        UniqueConstraint(
            "provider",
            "provider_subscription_id",
            name="uq_subscriptions_provider_subscription",
        ),
        CheckConstraint(
            "(provider = 'revenuecat' AND revenuecat_subscriber_id IS NOT NULL) OR "
            "(provider <> 'revenuecat' AND provider_subscription_id IS NOT NULL)",
            name="ck_subscriptions_provider_identifiers",
        ),
    )

    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        if self.status != "active":
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
