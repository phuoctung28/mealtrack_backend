"""
Repository for managing subscription database operations.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.infra.database.models.subscription import Subscription
from src.infra.repositories.base import BaseRepository
from src.domain.utils.timezone_utils import utc_now


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for subscription data operations."""
    
    def __init__(self, session: Session):
        super().__init__(Subscription, session)
    
    def find_all_by_user_id(self, user_id: str) -> List[Subscription]:
        """Find all subscriptions for a user."""
        return self.session.query(Subscription).filter(
            Subscription.user_id == user_id
        ).all()
    
    def get_by_user_id(self, user_id: str) -> List[Subscription]:
        """Get all subscriptions for a user (deprecated - use find_all_by_user_id)."""
        return self.find_all_by_user_id(user_id)
    
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
        """Async wrapper for get_by_user_id."""
        return self.get_by_user_id(user_id)
    
    async def get_by_revenuecat_id_async(self, revenuecat_subscriber_id: str) -> Optional[Subscription]:
        """Async wrapper for get_by_revenuecat_id."""
        return self.get_by_revenuecat_id(revenuecat_subscriber_id)