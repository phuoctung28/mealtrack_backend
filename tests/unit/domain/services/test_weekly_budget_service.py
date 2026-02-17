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
        """Test adjusted daily calculation when under budget."""
        # Create a budget with some consumption
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-1",
            user_id="user-1",
            week_start_date=date(2026, 2, 16),
            target_calories=14000,  # 2000 * 7
            target_protein=490,
            target_carbs=1400,
            target_fat=490,
            consumed_calories=6000,  # 3 days at 2000
            consumed_protein=210,
            consumed_carbs=600,
            consumed_fat=210,
            cheat_slots_total=2,
            cheat_slots_used=0,
        )

        # 4 days remaining (Wed, Thu, Fri, Sat)
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=2000,
            standard_daily_carbs=200,
            standard_daily_fat=70,
            standard_daily_protein=70,
            bmr=1600,
            remaining_days=4,
        )

        # Remaining: 14000 - 6000 = 8000 / 4 = 2000 kcal/day
        assert result.calories == 2000
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
            cheat_slots_total=2,
            cheat_slots_used=0,
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

    def test_should_suggest_cheat_tag_above_threshold(self):
        """Test smart prompt triggers above 120% threshold."""
        result = WeeklyBudgetService.should_suggest_cheat_tag(
            daily_consumed=2500,  # 125% of 2000
            daily_target=2000,
            meal_calories=500,
            meal_is_cheat=False,
        )

        assert result == "suggest_cheat_tag"

    def test_should_not_suggest_cheat_tag_below_threshold(self):
        """Test smart prompt doesn't trigger below threshold."""
        result = WeeklyBudgetService.should_suggest_cheat_tag(
            daily_consumed=1800,  # 90% of 2000
            daily_target=2000,
            meal_calories=500,
            meal_is_cheat=False,
        )

        assert result is None

    def test_should_not_suggest_for_already_cheat_meal(self):
        """Test no suggestion for meals already tagged as cheat."""
        result = WeeklyBudgetService.should_suggest_cheat_tag(
            daily_consumed=2500,
            daily_target=2000,
            meal_calories=500,
            meal_is_cheat=True,
        )

        assert result is None

    def test_get_cheat_slots_for_goal(self):
        """Test cheat slots are returned correctly for each goal."""
        assert WeeklyBudgetService.get_cheat_slots_for_goal("cut") == 2
        assert WeeklyBudgetService.get_cheat_slots_for_goal("bulk") == 3
        assert WeeklyBudgetService.get_cheat_slots_for_goal("recomp") == 4

    def test_get_cheat_slots_default(self):
        """Test default cheat slots for unknown goals."""
        assert WeeklyBudgetService.get_cheat_slots_for_goal("unknown") == 2

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

    def test_remaining_cheat_slots(self):
        """Test remaining cheat slots calculation."""
        budget = WeeklyMacroBudget(
            weekly_budget_id="test",
            user_id="user",
            week_start_date=date.today(),
            target_calories=14000,
            target_protein=490,
            target_carbs=1400,
            target_fat=490,
            cheat_slots_total=2,
            cheat_slots_used=1,
        )

        assert budget.remaining_cheat_slots == 1

    def test_use_cheat_slot(self):
        """Test using a cheat slot."""
        budget = WeeklyMacroBudget(
            weekly_budget_id="test",
            user_id="user",
            week_start_date=date.today(),
            target_calories=14000,
            target_protein=490,
            target_carbs=1400,
            target_fat=490,
            cheat_slots_total=2,
            cheat_slots_used=0,
        )

        result = budget.use_cheat_slot()
        assert result is True
        assert budget.cheat_slots_used == 1
        assert budget.remaining_cheat_slots == 1

    def test_use_cheat_slot_when_exhausted(self):
        """Test cannot use cheat slot when exhausted."""
        budget = WeeklyMacroBudget(
            weekly_budget_id="test",
            user_id="user",
            week_start_date=date.today(),
            target_calories=14000,
            target_protein=490,
            target_carbs=1400,
            target_fat=490,
            cheat_slots_total=2,
            cheat_slots_used=2,
        )

        result = budget.use_cheat_slot()
        assert result is False

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
