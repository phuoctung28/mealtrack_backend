"""
Unit tests: MacroValidationService.validate_deterministic

Verifies:
  - Logs tier distribution (T1/T2/T3 counts) at INFO level
  - Logs ERROR on zero or negative calories
  - Returns input MealMacros unchanged (pass-through validator)
"""
import logging
from unittest.mock import patch

import pytest

from src.domain.services.meal_suggestion.macro_validation_service import MacroValidationService
from src.domain.services.meal_suggestion.nutrition_lookup_service import (
    IngredientMacros,
    MealMacros,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ingredient(name: str, tier: str) -> IngredientMacros:
    return IngredientMacros(
        name=name,
        quantity_g=100.0,
        calories=100.0,
        protein=20.0,
        carbs=10.0,
        fat=3.0,
        fiber=1.0,
        sugar=0.5,
        source_tier=tier,
    )


def _make_meal_macros(
    calories: float = 450.0,
    t1: int = 2,
    t2: int = 1,
    t3: int = 0,
) -> MealMacros:
    ingredients = [
        _make_ingredient("chicken breast", "T1_food_reference"),
        _make_ingredient("rice", "T1_food_reference"),
        _make_ingredient("soy sauce", "T2_fatsecret"),
    ]
    return MealMacros(
        calories=calories,
        protein=50.0,
        carbs=40.0,
        fat=8.0,
        fiber=2.0,
        sugar=1.0,
        ingredients=ingredients,
        t1_count=t1,
        t2_count=t2,
        t3_count=t3,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidateDeterministic:
    def setup_method(self):
        self.service = MacroValidationService()

    def test_returns_input_unchanged(self):
        """validate_deterministic must not modify the MealMacros object."""
        meal_macros = _make_meal_macros(calories=450.0, t1=2, t2=1, t3=0)

        result = self.service.validate_deterministic(meal_macros)

        assert result is meal_macros, "Must return the same object (pass-through)"
        assert result.calories == 450.0
        assert result.protein == 50.0
        assert result.carbs == 40.0
        assert result.fat == 8.0
        assert result.t1_count == 2
        assert result.t2_count == 1
        assert result.t3_count == 0

    def test_logs_tier_distribution_info(self, caplog):
        """Tier distribution should be logged at INFO level."""
        meal_macros = _make_meal_macros(t1=3, t2=1, t3=2)

        with caplog.at_level(logging.INFO):
            self.service.validate_deterministic(meal_macros)

        assert any(
            "T1=3" in record.message and "T2=1" in record.message and "T3=2" in record.message
            for record in caplog.records
        ), f"Expected tier distribution log. Got: {[r.message for r in caplog.records]}"

    def test_logs_error_on_zero_calories(self, caplog):
        """Zero calories must trigger an ERROR log."""
        meal_macros = _make_meal_macros(calories=0.0)

        with caplog.at_level(logging.ERROR):
            self.service.validate_deterministic(meal_macros)

        error_logs = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert error_logs, "Expected ERROR log for zero calories"

    def test_logs_error_on_negative_calories(self, caplog):
        """Negative calories must trigger an ERROR log."""
        meal_macros = _make_meal_macros(calories=-10.0)

        with caplog.at_level(logging.ERROR):
            self.service.validate_deterministic(meal_macros)

        error_logs = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert error_logs, "Expected ERROR log for negative calories"

    def test_no_error_on_valid_positive_calories(self, caplog):
        """No ERROR logs when calories are positive."""
        meal_macros = _make_meal_macros(calories=600.0)

        with caplog.at_level(logging.ERROR):
            self.service.validate_deterministic(meal_macros)

        error_logs = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert not error_logs, f"Unexpected ERROR logs: {[r.message for r in error_logs]}"

    def test_all_t3_logs_tier_correctly(self, caplog):
        """Meals resolved entirely via AI fallback (T3) should log T3>0."""
        meal_macros = _make_meal_macros(t1=0, t2=0, t3=3)

        with caplog.at_level(logging.INFO):
            self.service.validate_deterministic(meal_macros)

        assert any(
            "T3=3" in record.message
            for record in caplog.records
        ), "Expected T3 count in log"
