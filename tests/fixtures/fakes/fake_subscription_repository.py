"""Fake subscription repository for testing."""
from datetime import datetime, timedelta
from typing import List, Optional

from src.domain.model.subscription import Subscription
from src.domain.ports.subscription_repository_port import SubscriptionRepositoryPort


class FakeSubscriptionRepository(SubscriptionRepositoryPort):
    """In-memory implementation of SubscriptionRepositoryPort for testing."""
    
    def __init__(self):
        self._subscriptions: dict[str, Subscription] = {}
    
    def save(self, subscription: Subscription) -> Subscription:
        """Save a subscription."""
        self._subscriptions[subscription.id] = subscription
        return subscription
    
    def find_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """Find a subscription by ID."""
        return self._subscriptions.get(subscription_id)
    
    def find_by_user_id(self, user_id: str) -> List[Subscription]:
        """Find all subscriptions for a user."""
        return [
            sub for sub in self._subscriptions.values()
            if sub.user_id == user_id
        ]
    
    def find_active_by_user_id(self, user_id: str) -> Optional[Subscription]:
        """Find active subscription for a user."""
        for sub in self._subscriptions.values():
            if (sub.user_id == user_id and 
                sub.status == "active" and
                (sub.expires_at is None or sub.expires_at > datetime.now())):
                return sub
        return None
    
    def find_expiring_soon(self, days_until_expiry: int = 7) -> List[Subscription]:
        """Find subscriptions expiring within specified days."""
        cutoff = datetime.now() + timedelta(days=days_until_expiry)
        return [
            sub for sub in self._subscriptions.values()
            if sub.expires_at and datetime.now() < sub.expires_at <= cutoff
        ]
    
    def cancel(self, subscription_id: str, reason: str = None) -> bool:
        """Cancel a subscription."""
        if subscription_id in self._subscriptions:
            sub = self._subscriptions[subscription_id]
            sub.status = "cancelled"
            return True
        return False
    
    def reactivate(self, subscription_id: str) -> bool:
        """Reactivate a cancelled subscription."""
        if subscription_id in self._subscriptions:
            sub = self._subscriptions[subscription_id]
            sub.status = "active"
            return True
        return False
    
    def update_payment_status(
        self, 
        subscription_id: str, 
        payment_status: str,
        payment_date: datetime = None
    ) -> bool:
        """Update payment status for a subscription."""
        if subscription_id in self._subscriptions:
            sub = self._subscriptions[subscription_id]
            sub.payment_status = payment_status
            if payment_date:
                sub.last_payment_date = payment_date
            return True
        return False
    
    def extend_trial(self, subscription_id: str, days: int) -> bool:
        """Extend trial period for a subscription."""
        if subscription_id in self._subscriptions:
            sub = self._subscriptions[subscription_id]
            if sub.trial_end_date:
                sub.trial_end_date = sub.trial_end_date + timedelta(days=days)
            return True
        return False
