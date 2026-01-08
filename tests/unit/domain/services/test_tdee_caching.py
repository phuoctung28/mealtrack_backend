"""
Unit tests for TDEE caching in SuggestionOrchestrationService.
"""
from unittest.mock import Mock, AsyncMock, patch

import pytest

from src.domain.cache.cache_keys import CacheKeys
from src.domain.services.meal_suggestion.suggestion_orchestration_service import (
    SuggestionOrchestrationService,
)


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_services():
    """Create mock services."""
    return {
        "generation_service": Mock(),
        "suggestion_repo": AsyncMock(),
        "user_repo": Mock(),
        "tdee_service": Mock(),
        "portion_service": Mock(),
    }


@pytest.fixture
def mock_profile():
    """Create mock user profile."""
    profile = Mock()
    profile.age = 30
    profile.gender = "male"
    profile.height_cm = 175
    profile.weight_kg = 75
    profile.activity_level = "moderate"
    profile.fitness_goal = "recomp"
    profile.body_fat_percentage = 18
    return profile


class TestTDEECaching:
    """Test TDEE caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_value(self, mock_redis_client, mock_services, mock_profile):
        """Cache hit should return cached TDEE without recalculating."""
        # Setup
        mock_redis_client.get.return_value = "2500.0"
        
        service = SuggestionOrchestrationService(
            **mock_services,
            redis_client=mock_redis_client,
        )
        
        # Execute
        result = await service._get_cached_tdee("user123", mock_profile)
        
        # Verify
        assert result == 2500.0
        mock_redis_client.get.assert_called_once()
        mock_redis_client.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_calculates_and_caches(self, mock_redis_client, mock_services, mock_profile):
        """Cache miss should calculate TDEE and cache it."""
        # Setup
        mock_redis_client.get.return_value = None
        
        service = SuggestionOrchestrationService(
            **mock_services,
            redis_client=mock_redis_client,
        )
        
        # Mock TDEE calculation
        mock_result = Mock()
        mock_result.macros.calories = 2200.0
        mock_services["tdee_service"].calculate_tdee.return_value = mock_result
        
        # Execute
        with patch.object(service, '_calculate_daily_tdee', return_value=2200.0):
            result = await service._get_cached_tdee("user123", mock_profile)
        
        # Verify
        assert result == 2200.0
        mock_redis_client.set.assert_called_once()
        
        # Verify TTL is 24h
        call_args = mock_redis_client.set.call_args
        assert call_args[0][2] == CacheKeys.TTL_1_DAY

    @pytest.mark.asyncio
    async def test_no_redis_falls_back_to_calculation(self, mock_services, mock_profile):
        """Without Redis, should calculate directly."""
        service = SuggestionOrchestrationService(
            **mock_services,
            redis_client=None,
        )
        
        mock_result = Mock()
        mock_result.macros.calories = 2000.0
        mock_services["tdee_service"].calculate_tdee.return_value = mock_result
        
        with patch.object(service, '_calculate_daily_tdee', return_value=2000.0):
            result = await service._get_cached_tdee("user123", mock_profile)
        
        assert result == 2000.0

    @pytest.mark.asyncio
    async def test_cache_error_falls_back_gracefully(self, mock_redis_client, mock_services, mock_profile):
        """Cache errors should fall back to calculation."""
        mock_redis_client.get.side_effect = Exception("Redis error")
        
        service = SuggestionOrchestrationService(
            **mock_services,
            redis_client=mock_redis_client,
        )
        
        with patch.object(service, '_calculate_daily_tdee', return_value=2100.0):
            result = await service._get_cached_tdee("user123", mock_profile)
        
        assert result == 2100.0


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_user_tdee_key_format(self):
        """TDEE cache key should have correct format."""
        key, ttl = CacheKeys.user_tdee("user123")
        
        assert key == "user:tdee:user123"
        assert ttl == CacheKeys.TTL_1_DAY

    def test_user_tdee_key_unique_per_user(self):
        """Different users should have different cache keys."""
        key1, _ = CacheKeys.user_tdee("user1")
        key2, _ = CacheKeys.user_tdee("user2")
        
        assert key1 != key2
