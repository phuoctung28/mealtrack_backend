"""
Unit tests for Subscription model.
"""
from datetime import datetime, timedelta

from src.infra.database.models.subscription import Subscription


class TestSubscriptionModel:
    """Test suite for Subscription model."""
    
    def test_subscription_is_active_when_status_active_and_not_expired(self):
        """Test that subscription is active when status is active and not expired."""
        subscription = Subscription(
            id="sub_123",
            user_id="user_123",
            revenuecat_subscriber_id="rc_123",
            product_id="premium_monthly",
            platform="ios",
            status="active",
            purchased_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30)
        )
        
        assert subscription.is_active() is True
    
    def test_subscription_not_active_when_expired(self):
        """Test that subscription is not active when expired."""
        subscription = Subscription(
            id="sub_123",
            user_id="user_123",
            revenuecat_subscriber_id="rc_123",
            product_id="premium_monthly",
            platform="ios",
            status="active",
            purchased_at=datetime.now() - timedelta(days=31),
            expires_at=datetime.now() - timedelta(days=1)
        )
        
        assert subscription.is_active() is False
    
    def test_subscription_not_active_when_status_not_active(self):
        """Test that subscription is not active when status is not active."""
        subscription = Subscription(
            id="sub_123",
            user_id="user_123",
            revenuecat_subscriber_id="rc_123",
            product_id="premium_monthly",
            platform="ios",
            status="cancelled",
            purchased_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30)
        )
        
        assert subscription.is_active() is False
    
    def test_subscription_is_monthly(self):
        """Test monthly subscription detection."""
        subscription = Subscription(
            id="sub_123",
            user_id="user_123",
            revenuecat_subscriber_id="rc_123",
            product_id="premium_monthly",
            platform="ios",
            status="active",
            purchased_at=datetime.now()
        )
        
        assert subscription.is_monthly() is True
        assert subscription.is_yearly() is False
    
    def test_subscription_is_yearly(self):
        """Test yearly subscription detection."""
        subscription = Subscription(
            id="sub_123",
            user_id="user_123",
            revenuecat_subscriber_id="rc_123",
            product_id="premium_yearly",
            platform="ios",
            status="active",
            purchased_at=datetime.now()
        )
        
        assert subscription.is_yearly() is True
        assert subscription.is_monthly() is False
    
    def test_subscription_is_yearly_with_annual_keyword(self):
        """Test yearly subscription detection with 'annual' keyword."""
        subscription = Subscription(
            id="sub_123",
            user_id="user_123",
            revenuecat_subscriber_id="rc_123",
            product_id="premium_annual",
            platform="ios",
            status="active",
            purchased_at=datetime.now()
        )
        
        assert subscription.is_yearly() is True
        assert subscription.is_monthly() is False
    
    def test_subscription_with_no_expiry_is_active(self):
        """Test that subscription with no expiry date is active if status is active."""
        subscription = Subscription(
            id="sub_123",
            user_id="user_123",
            revenuecat_subscriber_id="rc_123",
            product_id="premium_lifetime",
            platform="ios",
            status="active",
            purchased_at=datetime.now(),
            expires_at=None  # Lifetime subscription
        )
        
        assert subscription.is_active() is True