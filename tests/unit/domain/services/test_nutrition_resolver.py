"""Tests for deterministic nutrition resolution."""

import pytest
from pydantic import ValidationError

from src.domain.model.ai.vision_food_identity_contract import (
    VisionFoodIdentityResponse,
)
from src.domain.services.nutrition_resolver import (
    NutritionCandidate,
    NutritionResolver,
    select_nutrition_candidate,
    validate_ai_fallback,
    validate_reference_candidate,
)


@pytest.mark.asyncio
async def test_resolver_scales_nutrients_per_100g():
    resolver = NutritionResolver(
        local_candidates={
            "grilled chicken breast": NutritionCandidate(
                name="grilled chicken breast",
                protein_per_100g=31.0,
                carbs_per_100g=0.0,
                fat_per_100g=3.6,
                fiber_per_100g=0.0,
                sugar_per_100g=0.0,
                source="local",
            )
        }
    )

    result = await resolver.resolve_item(
        name="grilled chicken breast",
        estimated_grams=150.0,
    )

    assert result.name == "grilled chicken breast"
    assert result.grams == pytest.approx(150.0)
    assert result.macros.protein == pytest.approx(46.5)
    assert result.macros.carbs == pytest.approx(0.0)
    assert result.macros.fat == pytest.approx(5.4)
    assert result.source == "local"


@pytest.mark.asyncio
async def test_resolver_normalizes_lookup_key_and_rounds_scaled_macros():
    resolver = NutritionResolver(
        local_candidates={
            "banana": NutritionCandidate(
                name="banana",
                protein_per_100g=1.09,
                carbs_per_100g=22.84,
                fat_per_100g=0.33,
                fiber_per_100g=2.6,
                sugar_per_100g=12.23,
                source="local",
            )
        }
    )

    result = await resolver.resolve_item(name="  BANANA ", estimated_grams=118.0)

    assert result.macros.protein == pytest.approx(1.29)
    assert result.macros.carbs == pytest.approx(26.95)
    assert result.macros.fiber == pytest.approx(3.07)
    assert result.macros.sugar == pytest.approx(14.43)
    assert result.macros.total_calories == pytest.approx(110.3)


@pytest.mark.asyncio
async def test_resolver_rejects_missing_candidate():
    resolver = NutritionResolver(local_candidates={})

    with pytest.raises(ValueError, match="No nutrition candidate"):
        await resolver.resolve_item(name="mystery stew", estimated_grams=200.0)


def test_identity_contract_forbids_ai_macro_output():
    with pytest.raises(ValidationError):
        VisionFoodIdentityResponse.model_validate(
            {
                "is_food": True,
                "foods": [
                    {
                        "name": "rice",
                        "estimated_grams": 180.0,
                        "macros": {"protein": 4.0, "carbs": 50.0, "fat": 1.0},
                    }
                ],
            }
        )


def test_identity_contract_rejects_empty_food_image():
    with pytest.raises(ValidationError, match="foods must contain at least one item"):
        VisionFoodIdentityResponse.model_validate({"is_food": True, "foods": []})


def test_candidate_selection_rejects_risky_first_result_for_generic_food():
    selected = select_nutrition_candidate(
        [
            {"food_id": "concentrate", "food_name": "Potato concentrate"},
            {
                "food_id": "raw",
                "food_name": "Potato",
                "food_type": "Generic",
            },
        ],
        "potato",
    )

    assert selected is not None
    assert selected["food_id"] == "raw"


def test_candidate_selection_rejects_equal_score_tie():
    assert (
        select_nutrition_candidate(
            [
                {"food_id": "one", "food_name": "Potato"},
                {"food_id": "two", "food_name": "Potato"},
            ],
            "potato",
        )
        is None
    )


def test_candidate_selection_rejects_explicit_preparation_mismatch():
    assert (
        select_nutrition_candidate(
            [{"food_id": "egg", "food_name": "Egg"}],
            "egg",
            preparation="boiled",
        )
        is None
    )


def test_reference_validation_requires_metric_basis_for_provider_data():
    payload = {
        "protein_100g": 2,
        "carbs_100g": 17,
        "fat_100g": 0.1,
        "calories_100g": 77,
    }
    assert validate_reference_candidate(payload) is None
    payload["metric_serving_amount"] = 100
    assert validate_reference_candidate(payload) is not None


@pytest.mark.parametrize(
    "payload",
    [
        {"protein_100g": 80, "carbs_100g": 40, "fat_100g": 20, "calories_100g": 500},
        {"protein_100g": 2, "carbs_100g": 17, "calories_100g": 77},
        {"protein_100g": 2, "carbs_100g": 17, "fat_100g": 0.1, "calories_100g": 1000},
    ],
)
def test_reference_validation_rejects_incomplete_or_implausible_details(payload):
    assert validate_reference_candidate(payload) is None


def test_ai_fallback_rejects_potato_density_but_allows_oil_exception():
    assert not validate_ai_fallback(
        name="potato",
        protein=0,
        carbs=0,
        fat=98.9,
        quantity_g=100,
    )
    assert validate_ai_fallback(
        name="olive oil",
        protein=0,
        carbs=0,
        fat=10,
        quantity_g=10,
    )
