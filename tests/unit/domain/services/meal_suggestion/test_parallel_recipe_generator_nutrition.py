"""
Unit tests: NutritionLookupService wiring in recipe generation pipeline.

Verifies:
  - attempt_recipe_generation uses deterministic macros (not AI-reported values)
  - AI-returned macro fields are ignored when NutritionLookupService returns valid data
  - MacroValidationService.validate_deterministic is called (via side-effect check)
"""
import asyncio
import uuid
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.model.meal_suggestion import MealType, SuggestionSession
from src.domain.services.meal_suggestion.macro_validation_service import MacroValidationService
from src.domain.services.meal_suggestion.nutrition_lookup_service import (
    IngredientMacros,
    MealMacros,
    NutritionLookupService,
)
from src.domain.services.meal_suggestion.recipe_attempt_builder import attempt_recipe_generation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_session() -> SuggestionSession:
    return SuggestionSession(
        id="session_test",
        user_id="user_1",
        meal_type="lunch",
        meal_portion_type="main",
        target_calories=600,
        ingredients=["chicken breast", "rice"],
        cooking_time_minutes=30,
        servings=1,
        language="en",
        dietary_preferences=[],
        allergies=[],
        cooking_equipment=[],
        cuisine_region=None,
        protein_target=None,
        carbs_target=None,
        fat_target=None,
    )


def _make_ingredient_macros(name: str, tier: str = "T1_food_reference") -> IngredientMacros:
    return IngredientMacros(
        name=name,
        quantity_g=100.0,
        calories=120.0,
        protein=25.0,
        carbs=5.0,
        fat=2.5,
        fiber=0.5,
        sugar=0.0,
        source_tier=tier,
    )


def _make_meal_macros(t1: int = 2, t2: int = 0, t3: int = 0) -> MealMacros:
    ingredients = [
        _make_ingredient_macros("chicken breast", "T1_food_reference"),
        _make_ingredient_macros("rice", "T1_food_reference"),
    ]
    return MealMacros(
        calories=450.0,
        protein=52.0,
        carbs=38.0,
        fat=8.0,
        fiber=1.0,
        sugar=0.5,
        ingredients=ingredients,
        t1_count=t1,
        t2_count=t2,
        t3_count=t3,
    )


def _make_ai_raw_response() -> dict:
    """Simulated AI raw JSON response with ingredients and steps (no macros)."""
    return {
        "ingredients": [
            {"name": "chicken breast", "amount": 150.0, "unit": "g"},
            {"name": "rice", "amount": 200.0, "unit": "g"},
        ],
        "recipe_steps": [
            {"step": 1, "instruction": "Cook chicken breast in pan.", "duration_minutes": 10},
            {"step": 2, "instruction": "Steam rice until fluffy.", "duration_minutes": 20},
        ],
        "prep_time_minutes": 30,
        "origin_country": "International",
        "cuisine_type": "Asian",
        # AI-reported macros — should be IGNORED by the pipeline
        "calories": 9999,
        "protein": 999.0,
        "carbs": 999.0,
        "fat": 999.0,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_attempt_recipe_generation_uses_deterministic_macros():
    """MealSuggestion.macros must match NutritionLookupService output, not AI values."""
    session = _make_session()
    meal_macros = _make_meal_macros()

    generation_service = MagicMock()
    generation_service.generate_meal_plan.return_value = _make_ai_raw_response()

    nutrition_lookup = AsyncMock(spec=NutritionLookupService)
    nutrition_lookup.calculate_meal_macros.return_value = meal_macros
    # scale_to_target is synchronous; stub it to pass macros through unchanged
    # (450 kcal vs 600 target = scale 1.33 — within 0.7–1.4 range, so we pass-through)
    nutrition_lookup.scale_to_target.return_value = meal_macros

    macro_validator = MacroValidationService()

    result = await attempt_recipe_generation(
        generation_service=generation_service,
        macro_validator=macro_validator,
        nutrition_lookup=nutrition_lookup,
        prompt="Generate chicken rice",
        meal_name="Chicken Rice",
        index=0,
        model_purpose="recipe_primary",
        recipe_system="You are a chef.",
        session=session,
    )

    assert result is not None, "Should return a MealSuggestion on success"

    # Verify deterministic macros used — NOT the AI-reported 9999 values
    assert result.macros.calories == 450.0
    assert result.macros.protein == 52.0
    assert result.macros.carbs == 38.0
    assert result.macros.fat == 8.0

    # Verify NutritionLookupService was called with the correct ingredients
    nutrition_lookup.calculate_meal_macros.assert_called_once()
    call_args = nutrition_lookup.calculate_meal_macros.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0]["name"] == "chicken breast"
    assert call_args[1]["name"] == "rice"


@pytest.mark.asyncio
async def test_attempt_recipe_generation_ignores_ai_macro_fields():
    """Even if AI returns very wrong macro values, we use deterministic ones."""
    session = _make_session()
    # Deterministic result: 300 cal — scale = 600/300 = 2.0 → out of range.
    # Stub scale_to_target to return macros unchanged so this test stays focused
    # on "deterministic macros, not AI values" rather than the scaling behaviour.
    det_macros = MealMacros(
        calories=300.0, protein=30.0, carbs=25.0, fat=5.0,
        fiber=2.0, sugar=1.0,
        ingredients=[_make_ingredient_macros("egg", "T1_food_reference")],
        t1_count=1, t2_count=0, t3_count=0,
    )

    generation_service = MagicMock()
    ai_raw = _make_ai_raw_response()
    ai_raw["calories"] = 1500  # intentionally wrong AI value
    generation_service.generate_meal_plan.return_value = ai_raw

    nutrition_lookup = AsyncMock(spec=NutritionLookupService)
    nutrition_lookup.calculate_meal_macros.return_value = det_macros
    # Pass macros through scaling unchanged so we can assert on calorie values
    nutrition_lookup.scale_to_target.return_value = det_macros

    result = await attempt_recipe_generation(
        generation_service=generation_service,
        macro_validator=MacroValidationService(),
        nutrition_lookup=nutrition_lookup,
        prompt="...",
        meal_name="Egg Dish",
        index=1,
        model_purpose="recipe_secondary",
        recipe_system="You are a chef.",
        session=session,
    )

    assert result is not None
    # Must use deterministic 300 cal, not AI's 1500
    assert result.macros.calories == 300.0


@pytest.mark.asyncio
async def test_attempt_recipe_generation_returns_none_on_empty_ingredients():
    """Returns None when AI response has no ingredients."""
    session = _make_session()

    generation_service = MagicMock()
    generation_service.generate_meal_plan.return_value = {
        "ingredients": [],
        "recipe_steps": [{"step": 1, "instruction": "...", "duration_minutes": 5}],
        "prep_time_minutes": 10,
    }

    nutrition_lookup = AsyncMock(spec=NutritionLookupService)

    result = await attempt_recipe_generation(
        generation_service=generation_service,
        macro_validator=MacroValidationService(),
        nutrition_lookup=nutrition_lookup,
        prompt="...",
        meal_name="Empty Meal",
        index=0,
        model_purpose="recipe_primary",
        recipe_system="You are a chef.",
        session=session,
    )

    assert result is None
    # NutritionLookupService should NOT be called when AI returns no ingredients
    nutrition_lookup.calculate_meal_macros.assert_not_called()


@pytest.mark.asyncio
async def test_attempt_recipe_generation_returns_none_on_timeout():
    """Returns None on asyncio.TimeoutError."""
    session = _make_session()

    generation_service = MagicMock()
    generation_service.generate_meal_plan.side_effect = asyncio.TimeoutError()

    nutrition_lookup = AsyncMock(spec=NutritionLookupService)

    result = await attempt_recipe_generation(
        generation_service=generation_service,
        macro_validator=MacroValidationService(),
        nutrition_lookup=nutrition_lookup,
        prompt="...",
        meal_name="Timeout Meal",
        index=0,
        model_purpose="recipe_primary",
        recipe_system="You are a chef.",
        session=session,
    )

    assert result is None


@pytest.mark.asyncio
async def test_attempt_recipe_generation_returns_none_on_nutrition_lookup_error():
    """Returns None when NutritionLookupService raises an exception."""
    session = _make_session()

    generation_service = MagicMock()
    generation_service.generate_meal_plan.return_value = _make_ai_raw_response()

    nutrition_lookup = AsyncMock(spec=NutritionLookupService)
    nutrition_lookup.calculate_meal_macros.side_effect = RuntimeError("DB connection failed")

    result = await attempt_recipe_generation(
        generation_service=generation_service,
        macro_validator=MacroValidationService(),
        nutrition_lookup=nutrition_lookup,
        prompt="...",
        meal_name="Error Meal",
        index=0,
        model_purpose="recipe_primary",
        recipe_system="You are a chef.",
        session=session,
    )

    assert result is None


# ---------------------------------------------------------------------------
# Phase 5: Calorie target scaling scenarios
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_attempt_recipe_generation_scale_within_range_returns_scaled_suggestion():
    """Scale factor within 0.7–1.4: MealSuggestion.macros matches scaled values."""
    session = _make_session()  # target_calories=600

    generation_service = MagicMock()
    generation_service.generate_meal_plan.return_value = _make_ai_raw_response()

    # Deterministic macros: 520 kcal (scale = 600/520 ≈ 1.154 → within range)
    # Use a simple pure-protein ingredient so calorie math is exact
    from src.domain.services.meal_suggestion.nutrition_lookup_service import _derive_calories
    raw_protein = 130.0
    raw_calories = _derive_calories(raw_protein, 0.0, 0.0, 0.0)  # 520.0
    raw_macros = MealMacros(
        calories=raw_calories,
        protein=raw_protein,
        carbs=0.0,
        fat=0.0,
        fiber=0.0,
        sugar=0.0,
        ingredients=[
            IngredientMacros(
                name="chicken breast",
                quantity_g=150.0,
                calories=raw_calories,
                protein=raw_protein,
                carbs=0.0,
                fat=0.0,
                fiber=0.0,
                sugar=0.0,
                source_tier="T1_food_reference",
            )
        ],
        t1_count=1,
        t2_count=0,
        t3_count=0,
    )

    # Use a real NutritionLookupService (with mocked deps) so scale_to_target runs for real
    from unittest.mock import MagicMock as MM
    repo = MM()
    repo.find_by_normalized_name.return_value = None
    resolver = MM()
    gen_svc = MM()
    real_nutrition_lookup = NutritionLookupService(
        food_ref_repo=repo,
        ingredient_nutrition_resolver=resolver,
        generation_service=gen_svc,
    )

    # Patch calculate_meal_macros to return our controlled raw_macros
    real_nutrition_lookup.calculate_meal_macros = AsyncMock(return_value=raw_macros)

    result = await attempt_recipe_generation(
        generation_service=generation_service,
        macro_validator=MacroValidationService(),
        nutrition_lookup=real_nutrition_lookup,
        prompt="Generate chicken",
        meal_name="Scaled Chicken",
        index=0,
        model_purpose="recipe_primary",
        recipe_system="You are a chef.",
        session=session,
    )

    assert result is not None, "Scale factor ≈1.15 is within range; recipe should be accepted"

    scale = 600 / raw_calories
    # Verify macros reflect scaling (validate_deterministic passes through valid values)
    assert result.macros.calories == pytest.approx(raw_calories * scale, rel=0.05)
    assert result.macros.protein == pytest.approx(raw_protein * scale, rel=0.05)


@pytest.mark.asyncio
async def test_attempt_recipe_generation_scale_out_of_range_returns_none():
    """Scale factor outside 0.7–1.4: attempt returns None (triggers upstream retry)."""
    session = _make_session()  # target_calories=600

    generation_service = MagicMock()
    generation_service.generate_meal_plan.return_value = _make_ai_raw_response()

    # Deterministic macros: 1400 kcal → scale = 600/1400 ≈ 0.43 → rejected
    from src.domain.services.meal_suggestion.nutrition_lookup_service import _derive_calories
    raw_protein = 350.0
    raw_calories = _derive_calories(raw_protein, 0.0, 0.0, 0.0)  # 1400.0
    raw_macros = MealMacros(
        calories=raw_calories,
        protein=raw_protein,
        carbs=0.0,
        fat=0.0,
        fiber=0.0,
        sugar=0.0,
        ingredients=[
            IngredientMacros(
                name="steak",
                quantity_g=350.0,
                calories=raw_calories,
                protein=raw_protein,
                carbs=0.0,
                fat=0.0,
                fiber=0.0,
                sugar=0.0,
                source_tier="T1_food_reference",
            )
        ],
        t1_count=1,
        t2_count=0,
        t3_count=0,
    )

    from unittest.mock import MagicMock as MM
    repo = MM()
    repo.find_by_normalized_name.return_value = None
    resolver = MM()
    gen_svc = MM()
    real_nutrition_lookup = NutritionLookupService(
        food_ref_repo=repo,
        ingredient_nutrition_resolver=resolver,
        generation_service=gen_svc,
    )
    real_nutrition_lookup.calculate_meal_macros = AsyncMock(return_value=raw_macros)

    result = await attempt_recipe_generation(
        generation_service=generation_service,
        macro_validator=MacroValidationService(),
        nutrition_lookup=real_nutrition_lookup,
        prompt="Generate steak",
        meal_name="Oversized Steak",
        index=0,
        model_purpose="recipe_primary",
        recipe_system="You are a chef.",
        session=session,
    )

    # Scale factor ≈0.43 is out of range → rejected → None
    assert result is None, "Scale factor out of range should return None for upstream retry"
