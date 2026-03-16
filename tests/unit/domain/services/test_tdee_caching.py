"""
Unit tests for TDEE helper functions in suggestion_tdee_helpers.py.
"""
from unittest.mock import Mock, patch

import pytest

from src.domain.cache.cache_keys import CacheKeys
from src.domain.services.meal_suggestion.suggestion_tdee_helpers import (
    calculate_daily_tdee,
    get_adjusted_daily_target,
)


@pytest.fixture
def mock_tdee_service():
    """Create mock TDEE calculation service."""
    service = Mock()
    result = Mock()
    result.macros.calories = 2200.0
    result.bmr = 1800.0
    service.calculate_tdee.return_value = result
    return service


@pytest.fixture
def mock_profile():
    """Create mock user profile."""
    profile = Mock()
    profile.age = 30
    profile.gender = "male"
    profile.height_cm = 175
    profile.weight_kg = 75
    profile.job_type = "desk"
    profile.training_days_per_week = 4
    profile.training_minutes_per_session = 60
    profile.training_level = "intermediate"
    profile.fitness_goal = "recomp"
    profile.body_fat_percentage = 18
    return profile


class TestCalculateDailyTdee:
    """Test calculate_daily_tdee helper function."""

    def test_returns_calories_from_service(self, mock_tdee_service, mock_profile):
        """Should return calories from TDEE service calculation."""
        result = calculate_daily_tdee(mock_tdee_service, mock_profile)
        assert result == 2200.0
        mock_tdee_service.calculate_tdee.assert_called_once()

    def test_falls_back_to_2000_on_error(self, mock_profile):
        """Should return 2000 if TDEE calculation raises an exception."""
        failing_service = Mock()
        failing_service.calculate_tdee.side_effect = Exception("TDEE error")

        result = calculate_daily_tdee(failing_service, mock_profile)
        assert result == 2000.0


class TestGetAdjustedDailyTarget:
    """Test get_adjusted_daily_target helper function."""

    @pytest.mark.asyncio
    async def test_returns_adjusted_when_budget_exists(self, mock_tdee_service, mock_profile):
        """Should return adjusted calories when weekly budget exists."""
        from datetime import date

        mock_budget = Mock()
        mock_adjusted = Mock()
        mock_adjusted.calories = 2100.0
        mock_adjusted.bmr_floor_active = False

        with patch("src.domain.services.meal_suggestion.suggestion_tdee_helpers.UnitOfWork") as mock_uow_cls, \
             patch("src.domain.services.meal_suggestion.suggestion_tdee_helpers.WeeklyBudgetService") as mock_budget_svc, \
             patch("src.domain.services.meal_suggestion.suggestion_tdee_helpers.get_user_monday", return_value=date(2026, 3, 9)), \
             patch("src.domain.utils.timezone_utils.resolve_user_timezone", return_value="UTC"), \
             patch("src.domain.utils.timezone_utils.user_today", return_value=date(2026, 3, 13)):

            mock_uow = Mock()
            mock_uow.__enter__ = Mock(return_value=mock_uow)
            mock_uow.__exit__ = Mock(return_value=False)
            mock_uow.weekly_budgets.find_by_user_and_week.return_value = mock_budget
            mock_uow_cls.return_value = mock_uow

            mock_budget_svc.calculate_remaining_days.return_value = 5
            mock_budget_svc.calculate_adjusted_daily.return_value = mock_adjusted

            result = await get_adjusted_daily_target(mock_tdee_service, "user123", mock_profile)

        assert result == 2100.0

    @pytest.mark.asyncio
    async def test_falls_back_to_raw_tdee_when_no_budget(self, mock_tdee_service, mock_profile):
        """Should fall back to raw TDEE when no weekly budget found."""
        with patch("src.domain.services.meal_suggestion.suggestion_tdee_helpers.UnitOfWork") as mock_uow_cls:
            mock_uow = Mock()
            mock_uow.__enter__ = Mock(return_value=mock_uow)
            mock_uow.__exit__ = Mock(return_value=False)
            mock_uow.weekly_budgets.find_by_user_and_week.return_value = None
            mock_uow_cls.return_value = mock_uow

            result = await get_adjusted_daily_target(mock_tdee_service, "user123", mock_profile)

        assert result == 2200.0

    @pytest.mark.asyncio
    async def test_falls_back_to_calculate_daily_tdee_on_error(self, mock_profile):
        """Should fall back to calculate_daily_tdee if adjusted target raises."""
        failing_service = Mock()
        failing_service.calculate_tdee.side_effect = [Exception("TDEE error")]

        with patch("src.domain.services.meal_suggestion.suggestion_tdee_helpers.UnitOfWork") as mock_uow_cls:
            mock_uow_cls.side_effect = Exception("DB error")

            result = await get_adjusted_daily_target(failing_service, "user123", mock_profile)

        assert result == 2000.0


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
