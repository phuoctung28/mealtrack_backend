"""
Unit tests for WeeklyBudgetService.
"""
import pytest
from datetime import date

from src.domain.model.weekly import WeeklyMacroBudget
from src.domain.services.weekly_budget_service import (
    WeeklyBudgetService,
    AdjustedDailyTargets,
)


class TestWeeklyBudgetService:
    """Test weekly budget calculations."""

    def test_calculate_adjusted_daily_normal(self):
        """Test adjusted daily calculation when under budget.

        Calories derived from macros: P×4 + C×4 + F×9.
        Daily: 70×4 + 200×4 + 70×9 = 280+800+630 = 1710 kcal/day.
        Weekly target: 1710×7 = 11970, consumed 3 days: 5130.
        Remaining: 6840 / 4 = 1710/day.
        """
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-1",
            user_id="user-1",
            week_start_date=date(2026, 2, 16),
            target_calories=11970,  # 1710 * 7 (macro-consistent)
            target_protein=490,     # 70 * 7
            target_carbs=1400,      # 200 * 7
            target_fat=490,         # 70 * 7
            consumed_calories=5130,  # 3 days at 1710
            consumed_protein=210,    # 3 * 70
            consumed_carbs=600,      # 3 * 200
            consumed_fat=210,        # 3 * 70
        )

        # 4 days remaining — macros: P=70, C=200, F=70 → 1710 kcal/day
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=1710,
            standard_daily_carbs=200,
            standard_daily_fat=70,
            standard_daily_protein=70,
            bmr=1400,
            remaining_days=4,
        )

        # Derived: 70×4 + 200×4 + 70×9 = 1710
        assert result.calories == 1710
        assert result.bmr_floor_active is False
        assert result.remaining_days == 4

    def test_calculate_adjusted_daily_with_bmr_floor(self):
        """Test BMR floor is applied when budget is low."""
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-2",
            user_id="user-1",
            week_start_date=date(2026, 2, 16),
            target_calories=14000,
            target_protein=490,
            target_carbs=1400,
            target_fat=490,
            consumed_calories=12000,  # Only 2000 left for 6 days
            consumed_protein=420,
            consumed_carbs=1200,
            consumed_fat=420,
        )

        # 6 days remaining, 2000 left = 333/day (below BMR floor of 1600)
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=2000,
            standard_daily_carbs=200,
            standard_daily_fat=70,
            standard_daily_protein=70,
            bmr=1600,
            remaining_days=6,
        )

        # Should be capped at BMR floor
        assert result.calories == 1600
        assert result.bmr_floor_active is True

    def test_should_suggest_cheat_day_above_threshold(self):
        """Test cheat day suggestion triggers above threshold."""
        result = WeeklyBudgetService.should_suggest_cheat_day(
            daily_consumed=2500,  # 125% of 2000
            daily_target=2000,
            is_already_cheat_day=False,
        )
        assert result is True

    def test_should_not_suggest_cheat_day_below_threshold(self):
        """Test cheat day suggestion doesn't trigger below threshold."""
        result = WeeklyBudgetService.should_suggest_cheat_day(
            daily_consumed=1800,  # 90% of 2000
            daily_target=2000,
            is_already_cheat_day=False,
        )
        assert result is False

    def test_should_not_suggest_for_already_cheat_day(self):
        """Test no suggestion when already a cheat day."""
        result = WeeklyBudgetService.should_suggest_cheat_day(
            daily_consumed=2500,
            daily_target=2000,
            is_already_cheat_day=True,
        )
        assert result is False

    def test_calculate_remaining_days(self):
        """Test remaining days calculation."""
        # Monday to Sunday = 7 days
        monday = date(2026, 2, 16)
        assert WeeklyBudgetService.calculate_remaining_days(monday, monday) == 7

        # Wednesday = 5 days remaining
        wednesday = date(2026, 2, 18)
        assert WeeklyBudgetService.calculate_remaining_days(monday, wednesday) == 5

        # Next week = 0 days
        next_monday = date(2026, 2, 23)
        assert WeeklyBudgetService.calculate_remaining_days(monday, next_monday) == 0


class TestWeeklyMacroBudgetDomain:
    """Test WeeklyMacroBudget domain entity."""

    def test_remaining_calories(self):
        """Test remaining calories calculation."""
        budget = WeeklyMacroBudget(
            weekly_budget_id="test",
            user_id="user",
            week_start_date=date.today(),
            target_calories=14000,
            target_protein=490,
            target_carbs=1400,
            target_fat=490,
            consumed_calories=6000,
        )

        assert budget.remaining_calories == 8000

    def test_consumption_percentage(self):
        """Test consumption percentage calculation."""
        budget = WeeklyMacroBudget(
            weekly_budget_id="test",
            user_id="user",
            week_start_date=date.today(),
            target_calories=10000,
            target_protein=490,
            target_carbs=1400,
            target_fat=490,
            consumed_calories=5000,
        )

        assert budget.consumption_percentage == 50.0
