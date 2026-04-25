"""
Unit tests for WeeklyBudgetService.
"""

import pytest
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import List, Optional
from unittest.mock import MagicMock

from src.domain.model.meal import MealStatus
from src.domain.model.weekly import WeeklyMacroBudget
from src.domain.services.weekly_budget_service import (
    WeeklyBudgetService,
    AdjustedDailyTargets,
    EffectiveAdjustedResult,
)

# --- Fakes for testing get_effective_adjusted_daily / calculate_weekly_consumed ---


@dataclass
class FakeNutritionMacros:
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0


@dataclass
class FakeNutrition:
    calories: float = 0.0
    macros: FakeNutritionMacros = None

    def __post_init__(self):
        if self.macros is None:
            self.macros = FakeNutritionMacros()


@dataclass
class FakeMeal:
    status: MealStatus = MealStatus.READY
    nutrition: Optional[FakeNutrition] = None
    created_at: Optional[datetime] = None


@dataclass
class FakeCheatDay:
    date: date = None


class FakeMealRepo:
    """Fake meal repository with controllable data."""

    def __init__(self, meals: List[FakeMeal] = None, daily_counts: dict = None):
        self._meals = meals or []
        self._daily_counts = daily_counts or {}

    def find_by_date_range(self, user_id, start, end, user_timezone=None, **kwargs):
        return self._meals

    def get_daily_meal_counts(self, user_id, start, end, user_timezone=None):
        return self._daily_counts


class FakeCheatDayRepo:
    """Fake cheat day repository."""

    def __init__(self, cheat_days: List[FakeCheatDay] = None):
        self._cheat_days = cheat_days or []

    def find_by_user_and_date_range(self, user_id, start, end):
        return self._cheat_days


class FakeUoW:
    """Fake Unit of Work for testing."""

    def __init__(self, meals=None, daily_counts=None, cheat_days=None):
        self.meals = FakeMealRepo(meals or [], daily_counts or {})
        self.cheat_days = FakeCheatDayRepo(cheat_days or [])


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
            target_protein=490,  # 70 * 7
            target_carbs=1400,  # 200 * 7
            target_fat=490,  # 70 * 7
            consumed_calories=5130,  # 3 days at 1710
            consumed_protein=210,  # 3 * 70
            consumed_carbs=600,  # 3 * 200
            consumed_fat=210,  # 3 * 70
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
        """Test BMR floor activates when deficit cap still leaves calories below BMR.

        Uses a very high BMR (1900) that exceeds deficit cap (2000*0.9=1800).
        """
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

        # BMR=1900 > deficit cap floor (2000*0.9=1800), so BMR floor wins
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=2000,
            standard_daily_carbs=200,
            standard_daily_fat=70,
            standard_daily_protein=70,
            bmr=1900,
            remaining_days=6,
        )

        assert result.calories == 1900
        assert result.bmr_floor_active is True

    def test_deficit_cap_no_cap_needed(self):
        """Deficit within 10% — adjusted stays as-is, no cap distortion.

        Daily: P=70, C=200, F=70 → 1710/day. Weekly=11970.
        Consumed 4 days exactly at target: 6840. Remaining: 5130 / 3 = 1710.
        1710 == base → 0% deviation, no cap needed.
        """
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-cap-1",
            user_id="user-1",
            week_start_date=date(2026, 2, 16),
            target_calories=11970,  # 1710 * 7
            target_protein=490,
            target_carbs=1400,
            target_fat=490,
            consumed_calories=6840,
            consumed_protein=280,
            consumed_carbs=800,
            consumed_fat=280,
        )
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=1710,
            standard_daily_carbs=200,
            standard_daily_fat=70,
            standard_daily_protein=70,
            bmr=1400,
            remaining_days=3,
        )
        # Should equal base exactly (no cap needed)
        assert result.calories == 1710
        assert result.bmr_floor_active is False

    def test_deficit_cap_triggered_2000_base(self):
        """Deficit exceeds 10% for 2000-cal user — capped to 1800."""
        # Build budget so adjusted would be ~1700 without cap
        # Daily: P=70, C=200, F=70 → 1710/day, weekly=11970
        # Need remaining macros to produce ~1700/day with 2 days left
        # remaining_carbs/2 ~ 150, remaining_fat/2 ~ 50 → C=150, F=50
        # Calories from macros: 70*4 + 150*4 + 50*9 = 280+600+450 = 1330
        # That's way below cap, so cap will kick in
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-cap-2",
            user_id="user-1",
            week_start_date=date(2026, 2, 16),
            target_calories=11970,
            target_protein=490,
            target_carbs=1400,
            target_fat=490,
            consumed_calories=9600,
            consumed_protein=350,
            consumed_carbs=1100,
            consumed_fat=390,
        )
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=1710,
            standard_daily_carbs=200,
            standard_daily_fat=70,
            standard_daily_protein=70,
            bmr=1200,
            remaining_days=2,
        )
        # Cap: 1710 * 0.90 = 1539
        min_allowed = 1710 * 0.90
        assert result.calories >= min_allowed - 1  # tolerance for rounding
        assert result.protein == 70  # protein unchanged

    def test_deficit_cap_triggered_1500_base(self):
        """Deficit exceeds 10% for 1500-cal user — fairer than fixed -200."""
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-cap-3",
            user_id="user-1",
            week_start_date=date(2026, 2, 16),
            target_calories=10500,  # 1500 * 7
            target_protein=420,  # 60 * 7
            target_carbs=1312.5,  # 187.5 * 7
            target_fat=350,  # 50 * 7
            consumed_calories=9000,
            consumed_protein=360,
            consumed_carbs=1200,
            consumed_fat=310,
        )
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=1500,
            standard_daily_carbs=187.5,
            standard_daily_fat=50,
            standard_daily_protein=60,
            bmr=1100,
            remaining_days=2,
        )
        # Cap: 1500 * 0.90 = 1350, much less than a fixed -200 (1300)
        min_allowed = 1500 * 0.90
        assert result.calories >= min_allowed - 1
        assert result.protein == 60

    def test_deficit_cap_protein_unchanged(self):
        """Protein stays fixed regardless of deficit cap activation."""
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-cap-prot",
            user_id="user-1",
            week_start_date=date(2026, 2, 16),
            target_calories=14000,
            target_protein=980,  # 140 * 7
            target_carbs=1400,
            target_fat=490,
            consumed_calories=13000,
            consumed_protein=840,
            consumed_carbs=1300,
            consumed_fat=460,
        )
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=2000,
            standard_daily_carbs=200,
            standard_daily_fat=70,
            standard_daily_protein=140,
            bmr=1400,
            remaining_days=1,
        )
        assert result.protein == 140  # never touched

    def test_under_eating_no_cap(self):
        """Under-eating (surplus) — no cap applied, surplus uncapped."""
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-cap-surplus",
            user_id="user-1",
            week_start_date=date(2026, 2, 16),
            target_calories=14000,
            target_protein=490,
            target_carbs=1400,
            target_fat=490,
            consumed_calories=3000,  # very low consumption
            consumed_protein=100,
            consumed_carbs=300,
            consumed_fat=100,
        )
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=2000,
            standard_daily_carbs=200,
            standard_daily_fat=70,
            standard_daily_protein=70,
            bmr=1400,
            remaining_days=4,
        )
        # Surplus: adjusted should be ABOVE base (no upward cap)
        assert result.calories > 2000
        assert result.bmr_floor_active is False

    def test_calorie_cap_fat_heavy_surplus(self):
        """Calorie cap: over-eating fat + under-eating carbs should NOT inflate target.

        Real user scenario: base=2456, consumed Mon-Wed heavy on fat/protein,
        light on carbs. Without cap, macro redistribution gives 2570 (+114).
        With cap, should be ~2417 (-39).
        """
        # Base daily: P=114, C=346.6, F=68.2 → 2456 cal
        # Weekly: P=798, C=2426.2, F=477.4 → 17192 cal
        # Consumed Mon-Wed: P=494, C=784, F=268 → ~7521 cal
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-cap-fat",
            user_id="user-1",
            week_start_date=date(2026, 3, 23),
            target_calories=17192,
            target_protein=798,
            target_carbs=2426.2,
            target_fat=477.4,
            consumed_calories=7521,
            consumed_protein=494,
            consumed_carbs=784,
            consumed_fat=268,
        )
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=2456,
            standard_daily_carbs=346.6,
            standard_daily_fat=68.2,
            standard_daily_protein=114,
            bmr=1400,
            remaining_days=4,
        )
        # Must be BELOW base (user is in calorie surplus)
        assert result.calories < 2456
        # Calorie-redistributed = (17192-7521)/4 = 2417.75
        assert result.calories == pytest.approx(2417, abs=5)
        assert result.protein == 114
        # Carbs should still be above base (preserves "eat more carbs" signal)
        assert result.carbs > 346.6
        # Fat should be below base (user over-ate fat)
        assert result.fat < 68.2

    def test_calorie_cap_not_applied_when_under_eating(self):
        """Calorie cap should NOT fire when user is under-eating overall.

        calorie_redistributed > standard_daily → second condition fails.
        """
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-cap-under",
            user_id="user-1",
            week_start_date=date(2026, 3, 23),
            target_calories=17192,
            target_protein=798,
            target_carbs=2426.2,
            target_fat=477.4,
            consumed_calories=5000,  # Well under target for 3 days
            consumed_protein=300,
            consumed_carbs=600,
            consumed_fat=150,
        )
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=2456,
            standard_daily_carbs=346.6,
            standard_daily_fat=68.2,
            standard_daily_protein=114,
            bmr=1400,
            remaining_days=4,
        )
        # Under-eating: adjusted should be ABOVE base
        assert result.calories > 2456

    def test_calorie_cap_macros_balanced_no_cap(self):
        """When macros are balanced, macro-derived ≈ calorie-redistributed. No cap."""
        # Consume exactly at base ratios for 3 days
        budget = WeeklyMacroBudget(
            weekly_budget_id="test-cap-balanced",
            user_id="user-1",
            week_start_date=date(2026, 3, 23),
            target_calories=17192,
            target_protein=798,
            target_carbs=2426.2,
            target_fat=477.4,
            consumed_calories=7368,  # 3 × 2456
            consumed_protein=342,  # 3 × 114
            consumed_carbs=1039.8,  # 3 × 346.6
            consumed_fat=204.6,  # 3 × 68.2
        )
        result = WeeklyBudgetService.calculate_adjusted_daily(
            weekly_budget=budget,
            standard_daily_calories=2456,
            standard_daily_carbs=346.6,
            standard_daily_fat=68.2,
            standard_daily_protein=114,
            bmr=1400,
            remaining_days=4,
        )
        # Balanced consumption: should be close to base
        assert result.calories == pytest.approx(2456, abs=5)

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


# --- Helper to build a standard weekly budget for effective adjusted tests ---


def _make_budget(
    week_start=date(2026, 3, 23),
    consumed_cal=0.0,
    consumed_p=0.0,
    consumed_c=0.0,
    consumed_f=0.0,
):
    """Weekly budget: 2000 cal/day → 14000/wk, P=70, C=250, F=70."""
    return WeeklyMacroBudget(
        weekly_budget_id="eff-test",
        user_id="user-1",
        week_start_date=week_start,
        target_calories=14000,
        target_protein=490,  # 70 * 7
        target_carbs=1750,  # 250 * 7
        target_fat=490,  # 70 * 7
        consumed_calories=consumed_cal,
        consumed_protein=consumed_p,
        consumed_carbs=consumed_c,
        consumed_fat=consumed_f,
    )


# Base daily values matching _make_budget
_BASE_CAL = 2000.0
_BASE_P = 70.0
_BASE_C = 250.0
_BASE_F = 70.0
_BMR = 1500.0


class TestCalculateWeeklyConsumed:
    """Tests for WeeklyBudgetService.calculate_weekly_consumed."""

    def test_no_meals_returns_zeros(self):
        uow = FakeUoW(meals=[])
        result = WeeklyBudgetService.calculate_weekly_consumed(
            uow,
            "user-1",
            date(2026, 3, 23),
        )
        assert result == {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}

    def test_sums_ready_meals(self):
        meals = [
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=500,
                    macros=FakeNutritionMacros(protein=30, carbs=50, fat=20),
                ),
                created_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
            ),
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=700,
                    macros=FakeNutritionMacros(protein=40, carbs=80, fat=25),
                ),
                created_at=datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc),
            ),
        ]
        uow = FakeUoW(meals=meals)
        result = WeeklyBudgetService.calculate_weekly_consumed(
            uow,
            "user-1",
            date(2026, 3, 23),
        )
        assert result["calories"] == 1200
        assert result["protein"] == 70
        assert result["carbs"] == 130
        assert result["fat"] == 45

    def test_excludes_non_ready_meals(self):
        meals = [
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=500,
                    macros=FakeNutritionMacros(protein=30, carbs=50, fat=20),
                ),
                created_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
            ),
            FakeMeal(
                status=MealStatus.PROCESSING,
                nutrition=FakeNutrition(
                    calories=999,
                    macros=FakeNutritionMacros(protein=99, carbs=99, fat=99),
                ),
                created_at=datetime(2026, 3, 23, 13, 0, tzinfo=timezone.utc),
            ),
        ]
        uow = FakeUoW(meals=meals)
        result = WeeklyBudgetService.calculate_weekly_consumed(
            uow,
            "user-1",
            date(2026, 3, 23),
        )
        assert result["calories"] == 500

    def test_exclude_date_skips_meals_on_that_date(self):
        meals = [
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=500,
                    macros=FakeNutritionMacros(protein=30, carbs=50, fat=20),
                ),
                created_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
            ),
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=700,
                    macros=FakeNutritionMacros(protein=40, carbs=80, fat=25),
                ),
                created_at=datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc),
            ),
        ]
        uow = FakeUoW(meals=meals)
        # Exclude March 25
        result = WeeklyBudgetService.calculate_weekly_consumed(
            uow,
            "user-1",
            date(2026, 3, 23),
            exclude_date=date(2026, 3, 25),
            user_timezone="UTC",
        )
        assert result["calories"] == 500

    def test_exclude_dates_skips_multiple_dates(self):
        meals = [
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=500,
                    macros=FakeNutritionMacros(protein=30, carbs=50, fat=20),
                ),
                created_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
            ),
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=600,
                    macros=FakeNutritionMacros(protein=35, carbs=60, fat=22),
                ),
                created_at=datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc),
            ),
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=700,
                    macros=FakeNutritionMacros(protein=40, carbs=80, fat=25),
                ),
                created_at=datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc),
            ),
        ]
        uow = FakeUoW(meals=meals)
        result = WeeklyBudgetService.calculate_weekly_consumed(
            uow,
            "user-1",
            date(2026, 3, 23),
            exclude_dates=[date(2026, 3, 23), date(2026, 3, 25)],
            user_timezone="UTC",
        )
        # Only March 24 meal counted
        assert result["calories"] == 600


class TestGetEffectiveAdjustedDaily:
    """Tests for WeeklyBudgetService.get_effective_adjusted_daily."""

    def test_monday_first_day_returns_base(self):
        """Monday: no past days, remaining=7, returns base daily targets."""
        week_start = date(2026, 3, 23)  # Monday
        budget = _make_budget(week_start)
        uow = FakeUoW(meals=[], daily_counts={})

        result = WeeklyBudgetService.get_effective_adjusted_daily(
            uow=uow,
            user_id="user-1",
            week_start=week_start,
            target_date=week_start,
            weekly_budget=budget,
            base_daily_cal=_BASE_CAL,
            base_daily_protein=_BASE_P,
            base_daily_carbs=_BASE_C,
            base_daily_fat=_BASE_F,
            bmr=_BMR,
            cheat_dates=[],
        )
        assert result.show_logging_prompt is False
        assert result.skipped_days == 0
        assert result.logged_past_days == 0
        assert result.adjusted.remaining_days == 7

    def test_midweek_with_logged_days_prorates(self):
        """Wednesday with Mon/Tue logged: prorates over (2 logged + 5 remaining) = 7 effective days."""
        week_start = date(2026, 3, 23)
        wednesday = date(2026, 3, 25)
        # Mon+Tue meals: 1800 cal each = 3600 total
        meals = [
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=1800,
                    macros=FakeNutritionMacros(protein=70, carbs=250, fat=40),
                ),
                created_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
            ),
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=1800,
                    macros=FakeNutritionMacros(protein=70, carbs=250, fat=40),
                ),
                created_at=datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc),
            ),
        ]
        # daily_counts: {Mon: 1, Tue: 1}
        daily_counts = {date(2026, 3, 23): 1, date(2026, 3, 24): 1}
        budget = _make_budget(week_start)
        uow = FakeUoW(meals=meals, daily_counts=daily_counts)

        result = WeeklyBudgetService.get_effective_adjusted_daily(
            uow=uow,
            user_id="user-1",
            week_start=week_start,
            target_date=wednesday,
            weekly_budget=budget,
            base_daily_cal=_BASE_CAL,
            base_daily_protein=_BASE_P,
            base_daily_carbs=_BASE_C,
            base_daily_fat=_BASE_F,
            bmr=_BMR,
            cheat_dates=[],
        )
        assert result.logged_past_days == 2
        assert result.skipped_days == 0
        assert result.show_logging_prompt is False
        assert result.adjusted.remaining_days == 5

    def test_midweek_fresh_no_meals_shows_logging_prompt(self):
        """Wednesday fresh (0 meals, 0 logged days, past_days=2 < 3): no prompt yet.
        Thursday fresh (0 meals, 0 logged days, past_days=3 >= 3): shows prompt."""
        week_start = date(2026, 3, 23)
        thursday = date(2026, 3, 26)  # 3 past days (Mon/Tue/Wed)
        budget = _make_budget(week_start)
        uow = FakeUoW(meals=[], daily_counts={})

        result = WeeklyBudgetService.get_effective_adjusted_daily(
            uow=uow,
            user_id="user-1",
            week_start=week_start,
            target_date=thursday,
            weekly_budget=budget,
            base_daily_cal=_BASE_CAL,
            base_daily_protein=_BASE_P,
            base_daily_carbs=_BASE_C,
            base_daily_fat=_BASE_F,
            bmr=_BMR,
            cheat_dates=[],
        )
        # total_logged = 0 + 1 = 1 < MIN_LOGGED(3), past_days=3 >= 3 → prompt
        assert result.show_logging_prompt is True
        assert result.skipped_days == 3
        # When show_logging_prompt, returns base targets (remaining=7)
        assert result.adjusted.remaining_days == 7

    def test_cheat_day_excluded_from_redistribution(self):
        """Cheat day consumption excluded from redistribution math."""
        week_start = date(2026, 3, 23)
        wednesday = date(2026, 3, 25)
        # Mon: normal meal, Tue: cheat day binge
        meals = [
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=2000,
                    macros=FakeNutritionMacros(protein=70, carbs=250, fat=70),
                ),
                created_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
            ),
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=4000,
                    macros=FakeNutritionMacros(protein=100, carbs=500, fat=150),
                ),
                created_at=datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc),
            ),
        ]
        daily_counts = {date(2026, 3, 23): 1, date(2026, 3, 24): 1}
        budget = _make_budget(week_start)
        uow = FakeUoW(meals=meals, daily_counts=daily_counts)

        # With cheat day on Tue
        result_with_cheat = WeeklyBudgetService.get_effective_adjusted_daily(
            uow=uow,
            user_id="user-1",
            week_start=week_start,
            target_date=wednesday,
            weekly_budget=budget,
            base_daily_cal=_BASE_CAL,
            base_daily_protein=_BASE_P,
            base_daily_carbs=_BASE_C,
            base_daily_fat=_BASE_F,
            bmr=_BMR,
            cheat_dates=[date(2026, 3, 24)],
        )

        # Without cheat day
        result_no_cheat = WeeklyBudgetService.get_effective_adjusted_daily(
            uow=uow,
            user_id="user-1",
            week_start=week_start,
            target_date=wednesday,
            weekly_budget=budget,
            base_daily_cal=_BASE_CAL,
            base_daily_protein=_BASE_P,
            base_daily_carbs=_BASE_C,
            base_daily_fat=_BASE_F,
            bmr=_BMR,
            cheat_dates=[],
        )

        # Budget cap: both are capped at actual_remaining / remaining_days (8000/5=1600)
        # Cheat exclusion changes macro distribution but not total calories
        assert result_with_cheat.adjusted.calories == result_no_cheat.adjusted.calories
        # Macros may differ due to different redistribution paths
        assert result_with_cheat.adjusted.carbs != result_no_cheat.adjusted.carbs

    def test_cheat_dates_none_auto_loads(self):
        """When cheat_dates=None, auto-loads from uow.cheat_days."""
        week_start = date(2026, 3, 23)
        wednesday = date(2026, 3, 25)
        meals = [
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=2000,
                    macros=FakeNutritionMacros(protein=70, carbs=250, fat=70),
                ),
                created_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
            ),
        ]
        daily_counts = {date(2026, 3, 23): 1}
        cheat_days = [FakeCheatDay(date=date(2026, 3, 24))]
        budget = _make_budget(week_start)
        uow = FakeUoW(meals=meals, daily_counts=daily_counts, cheat_days=cheat_days)

        # cheat_dates=None → auto-load
        result = WeeklyBudgetService.get_effective_adjusted_daily(
            uow=uow,
            user_id="user-1",
            week_start=week_start,
            target_date=wednesday,
            weekly_budget=budget,
            base_daily_cal=_BASE_CAL,
            base_daily_protein=_BASE_P,
            base_daily_carbs=_BASE_C,
            base_daily_fat=_BASE_F,
            bmr=_BMR,
            cheat_dates=None,
        )
        # Should not raise, and should have processed cheat day
        assert result.adjusted is not None

    def test_sunday_last_day(self):
        """Sunday: remaining_days=1, all previous consumed."""
        week_start = date(2026, 3, 23)
        sunday = date(2026, 3, 29)
        # 6 days of meals consumed
        meals = [
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=2000,
                    macros=FakeNutritionMacros(protein=70, carbs=250, fat=70),
                ),
                created_at=datetime(2026, 3, 23 + i, 12, 0, tzinfo=timezone.utc),
            )
            for i in range(6)
        ]
        daily_counts = {date(2026, 3, 23 + i): 1 for i in range(6)}
        budget = _make_budget(week_start)
        uow = FakeUoW(meals=meals, daily_counts=daily_counts)

        result = WeeklyBudgetService.get_effective_adjusted_daily(
            uow=uow,
            user_id="user-1",
            week_start=week_start,
            target_date=sunday,
            weekly_budget=budget,
            base_daily_cal=_BASE_CAL,
            base_daily_protein=_BASE_P,
            base_daily_carbs=_BASE_C,
            base_daily_fat=_BASE_F,
            bmr=_BMR,
            cheat_dates=[],
        )
        assert result.adjusted.remaining_days == 1
        assert result.logged_past_days == 6

    def test_consumed_total_and_before_today_returned(self):
        """Verifies consumed_total and consumed_before_today populated."""
        week_start = date(2026, 3, 23)
        tuesday = date(2026, 3, 24)
        meals = [
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=500,
                    macros=FakeNutritionMacros(protein=30, carbs=50, fat=20),
                ),
                created_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
            ),
            FakeMeal(
                status=MealStatus.READY,
                nutrition=FakeNutrition(
                    calories=700,
                    macros=FakeNutritionMacros(protein=40, carbs=80, fat=25),
                ),
                created_at=datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc),
            ),
        ]
        daily_counts = {date(2026, 3, 23): 1}
        budget = _make_budget(week_start)
        uow = FakeUoW(meals=meals, daily_counts=daily_counts)

        result = WeeklyBudgetService.get_effective_adjusted_daily(
            uow=uow,
            user_id="user-1",
            week_start=week_start,
            target_date=tuesday,
            weekly_budget=budget,
            base_daily_cal=_BASE_CAL,
            base_daily_protein=_BASE_P,
            base_daily_carbs=_BASE_C,
            base_daily_fat=_BASE_F,
            bmr=_BMR,
            user_timezone="UTC",
            cheat_dates=[],
        )
        # consumed_total includes both days
        assert result.consumed_total["calories"] == 1200
        # consumed_before_today excludes Tuesday
        assert result.consumed_before_today["calories"] == 500
