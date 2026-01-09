"""
Unit tests for premium access middleware.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from src.api.middleware.premium_check import require_premium, get_premium_status


@pytest.mark.asyncio
class TestPremiumMiddleware:
    """Test suite for premium middleware."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request with user."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        return request
    
    @pytest.fixture
    def mock_user_with_premium(self):
        """Create mock user with active premium."""
        user = MagicMock()
        user.id = "user_123"
        user.is_premium.return_value = True
        
        subscription = MagicMock()
        subscription.product_id = "premium_monthly"
        subscription.expires_at = datetime.now() + timedelta(days=30)
        subscription.is_monthly.return_value = True
        subscription.is_yearly.return_value = False
        
        user.get_active_subscription.return_value = subscription
        return user
    
    @pytest.fixture
    def mock_user_without_premium(self):
        """Create mock user without premium."""
        user = MagicMock()
        user.id = "user_456"
        user.is_premium.return_value = False
        user.get_active_subscription.return_value = None
        return user
    
    async def test_require_premium_with_active_subscription(self, mock_request, mock_user_with_premium):
        """Test require_premium allows access with active subscription."""
        mock_request.state.user = mock_user_with_premium
        
        # Should not raise exception
        result = await require_premium(mock_request)
        assert result is None
    
    async def test_require_premium_without_user(self, mock_request):
        """Test require_premium requires authentication."""
        mock_request.state.user = None
        
        with pytest.raises(HTTPException) as exc_info:
            await require_premium(mock_request)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication required"
    
    async def test_require_premium_without_subscription_checks_revenuecat(
        self, mock_request, mock_user_without_premium
    ):
        """Test require_premium checks RevenueCat when no local subscription."""
        mock_request.state.user = mock_user_without_premium
        
        with patch('src.api.middleware.premium_check.os.getenv') as mock_getenv:
            mock_getenv.return_value = "test_key"
            
            with patch('src.api.middleware.premium_check.RevenueCatService') as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.is_premium_active = AsyncMock(return_value=True)
                
                # Should not raise exception - user has premium in RevenueCat
                result = await require_premium(mock_request)
                assert result is None
                mock_service.is_premium_active.assert_called_once_with(app_user_id="user_456")
    
    async def test_require_premium_denies_without_any_premium(
        self, mock_request, mock_user_without_premium
    ):
        """Test require_premium denies access when no premium anywhere."""
        mock_request.state.user = mock_user_without_premium
        
        with patch('src.api.middleware.premium_check.os.getenv') as mock_getenv:
            mock_getenv.return_value = "test_key"
            
            with patch('src.api.middleware.premium_check.RevenueCatService') as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.is_premium_active = AsyncMock(return_value=False)
                
                with pytest.raises(HTTPException) as exc_info:
                    await require_premium(mock_request)
                
                assert exc_info.value.status_code == 402
                assert exc_info.value.detail["error_code"] == "PREMIUM_REQUIRED"
    
    async def test_require_premium_without_revenuecat_config(
        self, mock_request, mock_user_without_premium
    ):
        """Test require_premium denies access when RevenueCat not configured."""
        mock_request.state.user = mock_user_without_premium
        
        with patch('src.api.middleware.premium_check.os.getenv') as mock_getenv:
            mock_getenv.return_value = ""
            
            with pytest.raises(HTTPException) as exc_info:
                await require_premium(mock_request)
            
            assert exc_info.value.status_code == 402
    
    async def test_get_premium_status_with_active_subscription(
        self, mock_request, mock_user_with_premium
    ):
        """Test get_premium_status returns correct info with subscription."""
        mock_request.state.user = mock_user_with_premium
        
        result = await get_premium_status(mock_request)
        
        assert result["is_premium"] is True
        assert result["subscription"]["product_id"] == "premium_monthly"
        assert result["subscription"]["is_monthly"] is True
        assert result["source"] == "cache"
    
    async def test_get_premium_status_without_user(self, mock_request):
        """Test get_premium_status without authenticated user."""
        mock_request.state.user = None
        
        result = await get_premium_status(mock_request)
        
        assert result["is_premium"] is False
        assert result["subscription"] is None
        assert result["source"] == "no_user"
    
    async def test_get_premium_status_checks_revenuecat(
        self, mock_request, mock_user_without_premium
    ):
        """Test get_premium_status checks RevenueCat when no local subscription."""
        mock_request.state.user = mock_user_without_premium
        
        with patch('src.api.middleware.premium_check.os.getenv') as mock_getenv:
            mock_getenv.return_value = "test_key"
            
            with patch('src.api.middleware.premium_check.RevenueCatService') as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.get_subscription_info = AsyncMock(return_value={
                    "product_id": "premium_yearly",
                    "expires_date": datetime.now() + timedelta(days=365),
                    "store": "APP_STORE",
                    "is_active": True
                })
                
                result = await get_premium_status(mock_request)
                
                assert result["is_premium"] is True
                assert result["subscription"]["product_id"] == "premium_yearly"
                assert result["source"] == "revenuecat_api"
    
    async def test_get_premium_status_no_premium(
        self, mock_request, mock_user_without_premium
    ):
        """Test get_premium_status when user has no premium."""
        mock_request.state.user = mock_user_without_premium
        
        with patch('src.api.middleware.premium_check.os.getenv') as mock_getenv:
            mock_getenv.return_value = "test_key"
            
            with patch('src.api.middleware.premium_check.RevenueCatService') as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.get_subscription_info = AsyncMock(return_value=None)
                
                result = await get_premium_status(mock_request)
                
                assert result["is_premium"] is False
                assert result["subscription"] is None
                assert result["source"] == "none"