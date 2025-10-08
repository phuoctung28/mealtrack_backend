"""
Unit tests for RevenueCat webhook handler.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.routes.v1.webhooks import (
    revenuecat_webhook,
    parse_platform,
    parse_timestamp,
    handle_purchase,
    handle_renewal,
    handle_cancellation,
    handle_expiration,
    handle_billing_issue
)


class TestWebhookHelpers:
    """Test webhook helper functions."""
    
    def test_parse_platform(self):
        """Test platform parsing from store name."""
        assert parse_platform("APP_STORE") == "ios"
        assert parse_platform("PLAY_STORE") == "android"
        assert parse_platform("STRIPE") == "web"
        assert parse_platform("MAC_APP_STORE") == "ios"
        assert parse_platform(None) == "ios"
        assert parse_platform("") == "ios"
        assert parse_platform("UNKNOWN") == "ios"
    
    def test_parse_timestamp(self):
        """Test timestamp parsing from milliseconds."""
        # Valid timestamp
        ms = 1696800000000  # Oct 8, 2023
        result = parse_timestamp(ms)
        assert isinstance(result, datetime)
        assert result.year == 2023
        
        # None timestamp
        assert parse_timestamp(None) is None
        
        # Zero timestamp
        assert parse_timestamp(0) is not None
        
        # Invalid timestamp
        with patch('src.api.routes.v1.webhooks.logger') as mock_logger:
            result = parse_timestamp("invalid")
            assert result is None


@pytest.mark.asyncio
class TestWebhookHandler:
    """Test webhook handler functions."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request object."""
        request = MagicMock()
        request.json = AsyncMock()
        return request
    
    @pytest.fixture
    def mock_uow(self):
        """Create mock Unit of Work."""
        uow = AsyncMock()
        uow.users = AsyncMock()
        uow.session = MagicMock()
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        return uow
    
    @pytest.fixture
    def webhook_event(self):
        """Create sample webhook event."""
        return {
            "event": {
                "type": "INITIAL_PURCHASE",
                "app_user_id": "user_123",
                "product_id": "premium_monthly",
                "store": "APP_STORE",
                "environment": "PRODUCTION",
                "purchased_at_ms": 1696800000000,
                "expiration_at_ms": 1699478400000,
                "transaction_id": "1000000123456789"
            }
        }
    
    async def test_webhook_success(self, mock_request, webhook_event):
        """Test successful webhook processing."""
        mock_request.json.return_value = webhook_event
        
        with patch('src.api.routes.v1.webhooks.UnitOfWork') as mock_uow_class:
            mock_uow = AsyncMock()
            mock_uow_class.return_value = mock_uow
            
            # Mock user exists
            mock_user = MagicMock(id="user_123")
            mock_uow.__aenter__.return_value.users.get.return_value = mock_user
            
            # Mock no existing subscription
            mock_uow.__aenter__.return_value.session.execute.return_value.scalar_one_or_none.return_value = None
            
            result = await revenuecat_webhook(mock_request, authorization=None)
            
            assert result == {"status": "success"}
            mock_uow.__aenter__.return_value.commit.assert_called_once()
    
    async def test_webhook_user_not_found(self, mock_request, webhook_event):
        """Test webhook when user not found."""
        mock_request.json.return_value = webhook_event
        
        with patch('src.api.routes.v1.webhooks.UnitOfWork') as mock_uow_class:
            mock_uow = AsyncMock()
            mock_uow_class.return_value = mock_uow
            
            # Mock user not found
            mock_uow.__aenter__.return_value.users.get.return_value = None
            
            result = await revenuecat_webhook(mock_request, authorization=None)
            
            assert result == {"status": "user_not_found"}
    
    async def test_webhook_invalid_json(self, mock_request):
        """Test webhook with invalid JSON."""
        mock_request.json.side_effect = Exception("Invalid JSON")
        
        with pytest.raises(HTTPException) as exc_info:
            await revenuecat_webhook(mock_request, authorization=None)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid JSON"
    
    async def test_webhook_authorization_check(self, mock_request, webhook_event):
        """Test webhook authorization check."""
        mock_request.json.return_value = webhook_event
        
        with patch('src.api.routes.v1.webhooks.settings') as mock_settings:
            mock_settings.REVENUECAT_WEBHOOK_SECRET = "secret_token"
            
            # Test with wrong authorization
            with pytest.raises(HTTPException) as exc_info:
                await revenuecat_webhook(mock_request, authorization="wrong_token")
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Unauthorized"
    
    async def test_handle_purchase(self, mock_uow):
        """Test handling initial purchase event."""
        user = MagicMock(id="user_123")
        event = {
            "app_user_id": "user_123",
            "product_id": "premium_monthly",
            "store": "APP_STORE",
            "purchased_at_ms": 1696800000000,
            "expiration_at_ms": 1699478400000,
            "transaction_id": "123456",
            "environment": "PRODUCTION"
        }
        
        # Mock no existing subscription
        mock_uow.session.execute.return_value.scalar_one_or_none.return_value = None
        
        await handle_purchase(mock_uow, user, event)
        
        # Verify subscription was added
        mock_uow.session.add.assert_called_once()
        added_subscription = mock_uow.session.add.call_args[0][0]
        assert added_subscription.user_id == "user_123"
        assert added_subscription.product_id == "premium_monthly"
        assert added_subscription.status == "active"
    
    async def test_handle_renewal(self, mock_uow):
        """Test handling renewal event."""
        user = MagicMock(id="user_123")
        subscription = MagicMock()
        event = {
            "app_user_id": "user_123",
            "expiration_at_ms": 1699478400000
        }
        
        # Mock existing subscription
        mock_uow.session.execute.return_value.scalar_one_or_none.return_value = subscription
        
        await handle_renewal(mock_uow, user, event)
        
        assert subscription.status == "active"
        assert subscription.expires_at is not None
    
    async def test_handle_cancellation(self, mock_uow):
        """Test handling cancellation event."""
        user = MagicMock(id="user_123")
        subscription = MagicMock()
        event = {"app_user_id": "user_123"}
        
        # Mock existing subscription
        mock_uow.session.execute.return_value.scalar_one_or_none.return_value = subscription
        
        await handle_cancellation(mock_uow, user, event)
        
        assert subscription.status == "cancelled"
        assert subscription.cancelled_at is not None
    
    async def test_handle_expiration(self, mock_uow):
        """Test handling expiration event."""
        user = MagicMock(id="user_123")
        subscription = MagicMock()
        event = {"app_user_id": "user_123"}
        
        # Mock existing subscription
        mock_uow.session.execute.return_value.scalar_one_or_none.return_value = subscription
        
        await handle_expiration(mock_uow, user, event)
        
        assert subscription.status == "expired"
    
    async def test_handle_billing_issue(self, mock_uow):
        """Test handling billing issue event."""
        user = MagicMock(id="user_123")
        subscription = MagicMock()
        event = {"app_user_id": "user_123"}
        
        # Mock existing subscription
        mock_uow.session.execute.return_value.scalar_one_or_none.return_value = subscription
        
        await handle_billing_issue(mock_uow, user, event)
        
        assert subscription.status == "billing_issue"