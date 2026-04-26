"""
Unit tests for async methods in WeeklyBudgetService.
"""
from datetime import date, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.services.weekly_budget_service import WeeklyBudgetService


class TestCalculateWeeklyConsumedAsync:
    """Test calculate_weekly_consumed_async method."""

    @pytest.mark.asyncio
    async def test_returns_zero_totals_when_no_meals(self):
        """Should return zero totals when no meals found."""
        mock_uow = Mock()
        mock_uow.meals.find_by_date_range = AsyncMock(return_value=[])

        result = await WeeklyBudgetService.calculate_weekly_consumed_async(
            uow=mock_uow,
            user_id="user123",
            week_start=date(2026, 3, 9),
        )

        assert result == {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}

    @pytest.mark.asyncio
    async def test_sums_ready_meals_only(self):
        """Should only sum meals with READY status."""
        from src.domain.model.meal import MealStatus

        ready_meal = Mock()
        ready_meal.status = MealStatus.READY
        ready_meal.nutrition.calories = 500
        ready_meal.nutrition.macros.protein = 30
        ready_meal.nutrition.macros.carbs = 60
        ready_meal.nutrition.macros.fat = 15
        ready_meal.created_at = None

        processing_meal = Mock()
        processing_meal.status = MealStatus.PROCESSING
        processing_meal.nutrition.calories = 300
        processing_meal.nutrition.macros.protein = 20
        processing_meal.nutrition.macros.carbs = 40
        processing_meal.nutrition.macros.fat = 10
        processing_meal.created_at = None

        mock_uow = Mock()
        mock_uow.meals.find_by_date_range = AsyncMock(return_value=[ready_meal, processing_meal])

        result = await WeeklyBudgetService.calculate_weekly_consumed_async(
            uow=mock_uow,
            user_id="user123",
            week_start=date(2026, 3, 9),
        )

        assert result["calories"] == 500
        assert result["protein"] == 30
        assert result["carbs"] == 60
        assert result["fat"] == 15


class TestGetEffectiveAdjustedDailyAsync:
    """Test get_effective_adjusted_daily_async method."""

    @pytest.mark.asyncio
    async def test_returns_base_targets_when_no_logging(self):
        """Should return base targets when insufficient logging data."""
        from dataclasses import dataclass

        @dataclass
        class MockBudget:
            target_calories: float = 14000
            target_protein: float = 1050
            target_carbs: float = 1750
            target_fat: float = 490
            consumed_calories: float = 0
            consumed_protein: float = 0
            consumed_carbs: float = 0
            consumed_fat: float = 0
            remaining_calories: float = 14000
            remaining_protein: float = 1050
            remaining_carbs: float = 1750
            remaining_fat: float = 490

        mock_uow = Mock()
        mock_uow.cheat_days.find_by_user_and_date_range = AsyncMock(return_value=[])
        mock_uow.meals.get_daily_meal_counts = AsyncMock(return_value={})
        mock_uow.meals.find_by_date_range = AsyncMock(return_value=[])

        week_start = date(2026, 3, 9)
        target_date = date(2026, 3, 13)  # Friday, 4 days into week

        result = await WeeklyBudgetService.get_effective_adjusted_daily_async(
            uow=mock_uow,
            user_id="user123",
            week_start=week_start,
            target_date=target_date,
            weekly_budget=MockBudget(),
            base_daily_cal=2000,
            base_daily_protein=150,
            base_daily_carbs=250,
            base_daily_fat=70,
            bmr=1600,
            user_timezone="UTC",
        )

        assert result.show_logging_prompt is True
        assert result.adjusted.calories > 0
