"""
SubscriptionRepositoryPort - Interface for subscription repository operations.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from src.domain.model.subscription import Subscription


class SubscriptionRepositoryPort(ABC):
    """Interface for subscription repository operations."""
    
    @abstractmethod
    def save(self, subscription: Subscription) -> Subscription:
        """Save or update a subscription."""
        pass
    
    @abstractmethod
    def find_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """Find a subscription by ID."""
        pass
    
    @abstractmethod
    def find_by_user_id(self, user_id: str) -> List[Subscription]:
        """Find all subscriptions for a user."""
        pass
    
    @abstractmethod
    def find_active_by_user_id(self, user_id: str) -> Optional[Subscription]:
        """Find the active subscription for a user."""
        pass
    
    @abstractmethod
    def find_expiring_soon(self, days_until_expiry: int = 7) -> List[Subscription]:
        """Find subscriptions expiring within specified days."""
        pass
    
    @abstractmethod
    def cancel(self, subscription_id: str, reason: str = None) -> bool:
        """Cancel a subscription."""
        pass
    
    @abstractmethod
    def reactivate(self, subscription_id: str) -> bool:
        """Reactivate a cancelled subscription."""
        pass
    
    @abstractmethod
    def update_payment_status(
        self, 
        subscription_id: str, 
        payment_status: str,
        payment_date: datetime = None
    ) -> bool:
        """Update payment status for a subscription."""
        pass
    
    @abstractmethod
    def extend_trial(self, subscription_id: str, days: int) -> bool:
        """Extend trial period for a subscription."""
        pass