"""
Repository for managing subscription database operations.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.domain.ports.subscription_repository_port import SubscriptionRepositoryPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.subscription import Subscription
from src.infra.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription], SubscriptionRepositoryPort):
    """Repository for subscription data operations."""

    def __init__(self, session: Session):
        super().__init__(Subscription, session)

    def save(self, subscription: Subscription) -> Subscription:
        """Save or update a subscription."""
        if subscription.subscription_id:
            return self.update(subscription)
        return self.add(subscription)

    def find_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """Find a subscription by ID."""
        return self.get(subscription_id)

    def find_by_user_id(self, user_id: str) -> List[Subscription]:
        """Find all subscriptions for a user."""
        return self.session.query(Subscription).filter(
            Subscription.user_id == user_id
        ).all()

    def find_all_by_user_id(self, user_id: str) -> List[Subscription]:
        """Find all subscriptions for a user (deprecated - use find_by_user_id)."""
        return self.find_by_user_id(user_id)

    def get_by_user_id(self, user_id: str) -> List[Subscription]:
        """Get all subscriptions for a user (deprecated - use find_by_user_id)."""
        return self.find_by_user_id(user_id)

    def find_active_by_user_id(self, user_id: str) -> Optional[Subscription]:
        """Find active subscription for a user."""
        return self.session.query(Subscription).filter(
            and_(
                Subscription.user_id == user_id,
                Subscription.status == 'active'
            )
        ).first()

    def get_active_by_user_id(self, user_id: str) -> Optional[Subscription]:
        """Get active subscription for a user (deprecated - use find_active_by_user_id)."""
        return self.find_active_by_user_id(user_id)

    def find_by_revenuecat_id(self, revenuecat_subscriber_id: str) -> Optional[Subscription]:
        """Find subscription by RevenueCat ID."""
        return self.session.query(Subscription).filter(
            Subscription.revenuecat_subscriber_id == revenuecat_subscriber_id
        ).first()

    def get_by_revenuecat_id(self, revenuecat_subscriber_id: str) -> Optional[Subscription]:
        """Get subscription by RevenueCat subscriber ID (deprecated - use find_by_revenuecat_id)."""
        return self.find_by_revenuecat_id(revenuecat_subscriber_id)

    def find_expiring_soon(self, days_until_expiry: int = 7) -> List[Subscription]:
        """Find subscriptions expiring within specified days."""
        from datetime import timedelta
        expiry_threshold = utc_now() + timedelta(days=days_until_expiry)
        return self.session.query(Subscription).filter(
            and_(
                Subscription.status == 'active',
                Subscription.expires_at <= expiry_threshold,
                Subscription.expires_at > utc_now()
            )
        ).all()

    def cancel(self, subscription_id: str, reason: str = None) -> bool:
        """Cancel a subscription."""
        subscription = self.get(subscription_id)
        if subscription:
            subscription.status = 'cancelled'
            subscription.updated_at = utc_now()
            if reason:
                subscription.cancellation_reason = reason
            self.session.commit()
            return True
        return False

    def reactivate(self, subscription_id: str) -> bool:
        """Reactivate a cancelled subscription."""
        subscription = self.get(subscription_id)
        if subscription and subscription.status == 'cancelled':
            subscription.status = 'active'
            subscription.updated_at = utc_now()
            self.session.commit()
            return True
        return False

    def extend_trial(self, subscription_id: str, days: int) -> bool:
        """Extend trial period for a subscription."""
        subscription = self.get(subscription_id)
        if subscription and subscription.status == 'trial':
            from datetime import timedelta
            if subscription.expires_at:
                subscription.expires_at = subscription.expires_at + timedelta(days=days)
            else:
                subscription.expires_at = utc_now() + timedelta(days=days)
            subscription.updated_at = utc_now()
            self.session.commit()
            return True
        return False

    def update_payment_status(
        self,
        subscription_id: str,
        payment_status: str,
        payment_date: datetime = None
    ) -> bool:
        """Update payment status for a subscription."""
        subscription = self.get(subscription_id)
        if subscription:
            subscription.payment_status = payment_status
            if payment_date:
                subscription.payment_date = payment_date
            subscription.updated_at = utc_now()
            self.session.commit()
            return True
        return False

    def get_expired_subscriptions(self) -> List[Subscription]:
        """Get all expired subscriptions that need status update."""
        return self.session.query(Subscription).filter(
            and_(
                Subscription.status == 'active',
                Subscription.expires_at < utc_now()
            )
        ).all()

    def update_subscription_status(
        self,
        subscription_id: str,
        status: str,
        expires_at: Optional[datetime] = None
    ) -> Optional[Subscription]:
        """Update subscription status."""
        subscription = self.get(subscription_id)
        if subscription:
            subscription.status = status
            subscription.updated_at = utc_now()
            if expires_at:
                subscription.expires_at = expires_at
            self.session.commit()
        return subscription

    # Async wrappers for compatibility
    async def get_by_user_id_async(self, user_id: str) -> List[Subscription]:
        """Async wrapper for find_by_user_id."""
        return self.find_by_user_id(user_id)

    async def get_by_revenuecat_id_async(self, revenuecat_subscriber_id: str) -> Optional[Subscription]:
        """Async wrapper for find_by_revenuecat_id."""
        return self.find_by_revenuecat_id(revenuecat_subscriber_id)
