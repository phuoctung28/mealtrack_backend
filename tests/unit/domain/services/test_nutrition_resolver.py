"""Tests for deterministic nutrition resolution."""

import pytest
from pydantic import ValidationError

from src.domain.model.ai.vision_food_identity_contract import (
    VisionFoodIdentityResponse,
)
from src.domain.services.nutrition_resolver import (
    NutritionCandidate,
    NutritionResolver,
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
