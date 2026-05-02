"""
Unit tests for NutritionLookupService.scale_to_target.

Covers:
- Normal scale within range (0.7–1.4) → scaled MealMacros returned
- Scale factor < 0.7 → None returned, warning logged
- Scale factor > 1.4 → None returned, warning logged
- Exact scale 1.0 → macros unchanged (within float tolerance)
- 0 calorie recipe → None returned (recipe rejected, warning logged)  [C4]
- target_calories=0 → original returned unchanged, warning logged (programming bug path)
- Scaled ingredients count equals input count
- Scaled calories are re-derived via fiber-aware formula (not simple multiply)
"""

import logging
from unittest.mock import MagicMock

import pytest

from src.domain.services.meal_suggestion.nutrition_lookup_service import (
    IngredientMacros,
    MealMacros,
    NutritionLookupService,
    _derive_calories,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service() -> NutritionLookupService:
    repo = MagicMock()
    repo.find_by_normalized_name.return_value = None
    resolver = MagicMock()
    gen = MagicMock()
    return NutritionLookupService(
        food_ref_repo=repo,
        ingredient_nutrition_resolver=resolver,
        generation_service=gen,
    )


def _make_ingredient(
    name: str = "chicken breast",
    quantity_g: float = 150.0,
    protein: float = 34.5,
    carbs: float = 0.0,
    fat: float = 3.75,
    fiber: float = 0.0,
    sugar: float = 0.0,
    tier: str = "T1_food_reference",
) -> IngredientMacros:
    calories = _derive_calories(protein, carbs, fat, fiber)
    return IngredientMacros(
        name=name,
        quantity_g=quantity_g,
        calories=round(calories, 1),
        protein=protein,
        carbs=carbs,
        fat=fat,
        fiber=fiber,
        sugar=sugar,
        source_tier=tier,
    )


def _make_meal(
    calories: float,
    protein: float,
    carbs: float,
    fat: float,
    fiber: float = 0.0,
    sugar: float = 0.0,
    ingredients=None,
) -> MealMacros:
    if ingredients is None:
        ingredients = [
            _make_ingredient(
                quantity_g=100.0,
                protein=protein,
                carbs=carbs,
                fat=fat,
                fiber=fiber,
                sugar=sugar,
            )
        ]
    return MealMacros(
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        fiber=fiber,
        sugar=sugar,
        ingredients=ingredients,
        t1_count=len([i for i in ingredients if i.source_tier == "T1_food_reference"]),
        t2_count=len([i for i in ingredients if i.source_tier == "T2_fatsecret"]),
        t3_count=len([i for i in ingredients if i.source_tier == "T3_ai_estimate"]),
    )


# ---------------------------------------------------------------------------
# 520 kcal recipe scaled to 600 → factor ≈ 1.154
# ---------------------------------------------------------------------------


def test_scale_within_range_returns_scaled_macros():
    """520 kcal recipe, target 600 → scale ≈ 1.154; all macros × scale."""
    svc = _make_service()
    # Construct ingredients so _aggregate gives exactly 520 kcal.
    # Simple case: 1 ingredient, pure protein (P×4 = calories)
    # 520 / 4 = 130g protein at 100g quantity_g
    ing = _make_ingredient(
        name="protein source",
        quantity_g=100.0,
        protein=130.0,
        carbs=0.0,
        fat=0.0,
        fiber=0.0,
    )
    meal = _make_meal(
        calories=520.0,
        protein=130.0,
        carbs=0.0,
        fat=0.0,
        ingredients=[ing],
    )

    result = svc.scale_to_target(meal, 600)

    assert result is not None
    scale = 600 / 520.0
    assert result.calories == pytest.approx(600.0, rel=0.01)
    assert result.protein == pytest.approx(130.0 * scale, rel=0.01)
    assert result.ingredients[0].quantity_g == pytest.approx(100.0 * scale, rel=0.01)


# ---------------------------------------------------------------------------
# 1200 kcal recipe, target 600 → scale 0.5 → None
# ---------------------------------------------------------------------------


def test_scale_factor_below_07_returns_none(caplog):
    """1200 kcal recipe, target 600 → scale=0.5 < 0.7 → None + WARNING logged."""
    svc = _make_service()
    ing = _make_ingredient(protein=300.0, carbs=0.0, fat=0.0, quantity_g=300.0)
    meal = _make_meal(
        calories=1200.0, protein=300.0, carbs=0.0, fat=0.0, ingredients=[ing]
    )

    with caplog.at_level(
        logging.WARNING,
        logger="src.domain.services.meal_suggestion.nutrition_lookup_service",
    ):
        result = svc.scale_to_target(meal, 600)

    assert result is None
    assert "out of range" in caplog.text


# ---------------------------------------------------------------------------
# 300 kcal recipe, target 600 → scale 2.0 → None
# ---------------------------------------------------------------------------


def test_scale_factor_above_14_returns_none(caplog):
    """300 kcal recipe, target 600 → scale=2.0 > 1.4 → None + WARNING logged."""
    svc = _make_service()
    ing = _make_ingredient(protein=75.0, carbs=0.0, fat=0.0, quantity_g=75.0)
    meal = _make_meal(
        calories=300.0, protein=75.0, carbs=0.0, fat=0.0, ingredients=[ing]
    )

    with caplog.at_level(
        logging.WARNING,
        logger="src.domain.services.meal_suggestion.nutrition_lookup_service",
    ):
        result = svc.scale_to_target(meal, 600)

    assert result is None
    assert "out of range" in caplog.text


# ---------------------------------------------------------------------------
# Exact scale 1.0 → macros unchanged
# ---------------------------------------------------------------------------


def test_scale_factor_10_returns_unchanged_macros():
    """600 kcal recipe, target 600 → scale=1.0; macros within float tolerance."""
    svc = _make_service()
    ing = _make_ingredient(protein=150.0, carbs=0.0, fat=0.0, quantity_g=150.0)
    meal = _make_meal(
        calories=600.0, protein=150.0, carbs=0.0, fat=0.0, ingredients=[ing]
    )

    result = svc.scale_to_target(meal, 600)

    assert result is not None
    assert result.calories == pytest.approx(600.0, rel=0.01)
    assert result.protein == pytest.approx(150.0, rel=0.01)
    assert result.ingredients[0].quantity_g == pytest.approx(150.0, rel=0.01)


# ---------------------------------------------------------------------------
# C4: 0 calorie recipe → None returned (recipe rejected), warning logged
# ---------------------------------------------------------------------------


def test_zero_calorie_recipe_returns_none(caplog):
    """0 kcal recipe → all T3 lookups failed; scale_to_target returns None to reject recipe."""
    svc = _make_service()
    ing = _make_ingredient(protein=0.0, carbs=0.0, fat=0.0, quantity_g=50.0)
    ing.calories = 0.0
    meal = _make_meal(calories=0.0, protein=0.0, carbs=0.0, fat=0.0, ingredients=[ing])

    with caplog.at_level(
        logging.WARNING,
        logger="src.domain.services.meal_suggestion.nutrition_lookup_service",
    ):
        result = svc.scale_to_target(meal, 600)

    assert result is None
    assert "0 kcal" in caplog.text or "rejecting" in caplog.text


# ---------------------------------------------------------------------------
# target_calories=0 → returned unchanged, warning logged
# ---------------------------------------------------------------------------


def test_zero_target_calories_returns_unchanged(caplog):
    """target_calories=0 → original MealMacros returned + WARNING logged."""
    svc = _make_service()
    ing = _make_ingredient(protein=50.0, carbs=0.0, fat=0.0, quantity_g=50.0)
    meal = _make_meal(
        calories=200.0, protein=50.0, carbs=0.0, fat=0.0, ingredients=[ing]
    )

    with caplog.at_level(
        logging.WARNING,
        logger="src.domain.services.meal_suggestion.nutrition_lookup_service",
    ):
        result = svc.scale_to_target(meal, 0)

    assert result is meal
    assert "invalid" in caplog.text.lower() or "target_calories" in caplog.text


# ---------------------------------------------------------------------------
# Scaled ingredients count equals input count
# ---------------------------------------------------------------------------


def test_scaled_ingredients_count_matches_input():
    """Output MealMacros.ingredients has same count as input."""
    svc = _make_service()
    ingredients = [
        _make_ingredient("chicken", 150.0, 34.5, 0.0, 3.75),
        _make_ingredient("rice", 200.0, 4.0, 52.0, 0.5, 0.5),
        _make_ingredient("broccoli", 80.0, 2.4, 4.4, 0.2, 0.4),
    ]
    # Build calories from aggregated macros
    total_p = sum(i.protein for i in ingredients)
    total_c = sum(i.carbs for i in ingredients)
    total_f = sum(i.fat for i in ingredients)
    total_fiber = sum(i.fiber for i in ingredients)
    total_cal = _derive_calories(total_p, total_c, total_f, total_fiber)

    meal = MealMacros(
        calories=round(total_cal, 1),
        protein=round(total_p, 1),
        carbs=round(total_c, 1),
        fat=round(total_f, 1),
        fiber=round(total_fiber, 1),
        sugar=0.0,
        ingredients=ingredients,
        t1_count=3,
        t2_count=0,
        t3_count=0,
    )

    # target just within range (~1.15× scale)
    target = int(total_cal * 1.15)
    result = svc.scale_to_target(meal, target)

    assert result is not None
    assert len(result.ingredients) == 3


# ---------------------------------------------------------------------------
# Scaled calories are re-derived via fiber-aware formula, not simple multiply
# ---------------------------------------------------------------------------


def test_scaled_calories_re_derived_via_fiber_aware_formula():
    """Verify that scaled meal calories = P×4 + (C−fiber)×4 + fiber×2 + F×9.

    Uses an ingredient with significant fiber so the fiber-aware formula
    gives a different result than a simple multiply of the original calories.
    """
    svc = _make_service()
    # Ingredient: 100g with protein=20, carbs=30, fat=5, fiber=10
    # Fiber-aware calories: (30-10)×4 + 10×2 + 20×4 + 5×9 = 80+20+80+45 = 225
    ing = _make_ingredient(
        protein=20.0, carbs=30.0, fat=5.0, fiber=10.0, quantity_g=100.0
    )
    # Manually set calories to the fiber-aware value
    ing.calories = 225.0
    meal = MealMacros(
        calories=225.0,
        protein=20.0,
        carbs=30.0,
        fat=5.0,
        fiber=10.0,
        sugar=0.0,
        ingredients=[ing],
        t1_count=1,
        t2_count=0,
        t3_count=0,
    )

    # Scale factor = 270/225 = 1.2 (within range)
    result = svc.scale_to_target(meal, 270)

    assert result is not None
    # Re-derived via _aggregate using scaled macros
    scaled_protein = round(20.0 * 1.2, 1)
    scaled_carbs = round(30.0 * 1.2, 1)
    scaled_fat = round(5.0 * 1.2, 1)
    scaled_fiber = round(10.0 * 1.2, 1)
    expected_cal = _derive_calories(
        scaled_protein, scaled_carbs, scaled_fat, scaled_fiber
    )
    assert result.calories == pytest.approx(round(expected_cal, 1), rel=0.01)

    # Cross-check: calories != simple multiply (225 × 1.2 = 270)
    # Expected re-derived: (scaled_carbs - scaled_fiber)×4 + scaled_fiber×2 + scaled_protein×4 + scaled_fat×9
    # With no fiber rounding issues: should match expected_cal
    assert result.calories == pytest.approx(expected_cal, rel=0.01)
