"""
Unit tests for async methods in WeeklyBudgetService.
"""
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.model.weekly import WeeklyMacroBudget
from src.domain.services.weekly_budget_service import WeeklyBudgetService


def _ready_meal(*, protein: float, carbs: float, fat: float, created_at: datetime):
    from src.domain.model.meal import MealStatus

    meal = Mock()
    meal.status = MealStatus.READY
    meal.created_at = created_at
    meal.nutrition.macros.protein = protein
    meal.nutrition.macros.carbs = carbs
    meal.nutrition.macros.fat = fat
    meal.nutrition.macros.fiber = 0.0
    return meal


class _FakeMovementEntries:
    def __init__(self, entries):
        self.entries = entries
        self.calls = []

    async def sum_included_kcal_for_range(self, user_id, start_utc, end_utc):
        self.calls.append((user_id, start_utc, end_utc))
        return sum(
            kcal
            for logged_at, kcal, include in self.entries
            if include and start_utc <= logged_at < end_utc
        )


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
        ready_meal.nutrition.calories = 9999
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

        assert result["calories"] == 495
        assert result["protein"] == 30
        assert result["carbs"] == 60
        assert result["fat"] == 15

    @pytest.mark.asyncio
    async def test_subtracts_included_movement_from_calories_only(self):
        """Movement credit affects calorie balance, not food macro grams."""
        meal = _ready_meal(
            protein=100,
            carbs=250,
            fat=100,
            created_at=datetime(2026, 3, 9, 12, tzinfo=UTC),
        )
        mock_uow = Mock()
        mock_uow.meals.find_by_date_range = AsyncMock(return_value=[meal])
        mock_uow.movement_entries = _FakeMovementEntries(
            [(datetime(2026, 3, 9, 18, tzinfo=UTC), 200.0, True)]
        )

        result = await WeeklyBudgetService.calculate_weekly_consumed_async(
            uow=mock_uow,
            user_id="user123",
            week_start=date(2026, 3, 9),
            user_timezone="UTC",
        )

        assert result["calories"] == 2100.0
        assert result["protein"] == 100
        assert result["carbs"] == 250
        assert result["fat"] == 100

    @pytest.mark.asyncio
    async def test_ignores_excluded_and_future_movement(self):
        """Only included movement inside the requested local date range counts."""
        meal = _ready_meal(
            protein=100,
            carbs=250,
            fat=100,
            created_at=datetime(2026, 3, 9, 12, tzinfo=UTC),
        )
        mock_uow = Mock()
        mock_uow.meals.find_by_date_range = AsyncMock(return_value=[meal])
        mock_uow.movement_entries = _FakeMovementEntries(
            [
                (datetime(2026, 3, 9, 18, tzinfo=UTC), 200.0, False),
                (datetime(2026, 3, 10, 18, tzinfo=UTC), 500.0, True),
            ]
        )

        result = await WeeklyBudgetService.calculate_weekly_consumed_async(
            uow=mock_uow,
            user_id="user123",
            week_start=date(2026, 3, 9),
            end_date=date(2026, 3, 9),
            user_timezone="UTC",
        )

        assert result["calories"] == 2300.0


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

    @pytest.mark.asyncio
    async def test_workout_credit_softens_next_day_adjustment(self):
        """2300 food - 200 movement behaves like 2100 weekly calories."""
        meal = _ready_meal(
            protein=100,
            carbs=250,
            fat=100,
            created_at=datetime(2026, 3, 9, 12, tzinfo=UTC),
        )

        mock_uow = Mock()
        mock_uow.cheat_days.find_by_user_and_date_range = AsyncMock(return_value=[])
        mock_uow.meals.get_daily_meal_counts = AsyncMock(
            return_value={date(2026, 3, 9): 1}
        )
        mock_uow.meals.find_by_date_range = AsyncMock(return_value=[meal])
        mock_uow.movement_entries = _FakeMovementEntries(
            [(datetime(2026, 3, 9, 18, tzinfo=UTC), 200.0, True)]
        )

        result = await WeeklyBudgetService.get_effective_adjusted_daily_async(
            uow=mock_uow,
            user_id="user123",
            week_start=date(2026, 3, 9),
            target_date=date(2026, 3, 10),
            weekly_budget=WeeklyMacroBudget(
                weekly_budget_id="budget-1",
                user_id="user123",
                week_start_date=date(2026, 3, 9),
                target_calories=14000,
                target_protein=700,
                target_carbs=1750,
                target_fat=466.6667,
            ),
            base_daily_cal=2000,
            base_daily_protein=100,
            base_daily_carbs=250,
            base_daily_fat=66.6667,
            bmr=1600,
            user_timezone="UTC",
        )

        assert result.consumed_before_today["calories"] == 2100.0
        assert result.consumed_total["calories"] == 2100.0
        assert result.consumed_total["protein"] == 100
        assert result.consumed_total["carbs"] == 250
        assert result.consumed_total["fat"] == 100
        assert result.adjusted.calories == pytest.approx(1983.3, abs=1.0)
