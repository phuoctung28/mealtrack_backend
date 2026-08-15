from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.app.commands.meal.create_manual_meal_command import (
    CustomNutrition,
    ManualMealItem,
)
from src.app.services.manual_meal_nutrition_resolver import (
    ManualMealNutritionResolver,
)
from src.domain.services.nutrition_integrity_policy import NutritionIntegrityError


def _reference(**overrides):
    values = {
        "id": 42,
        "name": "Rice",
        "source": "food_reference",
        "is_verified": True,
        "protein_100g": 2.7,
        "carbs_100g": 28.0,
        "fat_100g": 0.3,
        "fiber_100g": 0.4,
        "sugar_100g": 0.1,
        "servings": [SimpleNamespace(name="cup", grams=158, milliliters=None)],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class _References:
    async def get_nutrition_projection(self, food_reference_id):
        assert food_reference_id == 42
        return _reference()


@pytest.mark.asyncio
async def test_local_reference_ignores_client_nutrition_and_units():
    item = ManualMealItem(
        name="Rice",
        quantity=100,
        unit="g",
        origin="local",
        food_reference_id=42,
        custom_nutrition=CustomNutrition(
            calories_per_100g=900,
            protein_per_100g=100,
            carbs_per_100g=0,
            fat_per_100g=0,
        ),
        allowed_units=[{"unit": "evil", "gram_weight": 99999}],
    )

    resolved = await ManualMealNutritionResolver().resolve_items(
        [item], _References(), contract_version=2
    )

    assert resolved[0].custom_nutrition.protein_per_100g == pytest.approx(2.7)
    assert resolved[0].allowed_units == [
        {"unit": "g", "gram_weight": 1.0, "description": "1 g"},
        {"unit": "cup", "gram_weight": 158.0, "description": "cup"},
    ]
    assert resolved[0].source_kind == "local"
    assert resolved[0].source_snapshot["calories_per_100g"] == pytest.approx(124.7)


@pytest.mark.asyncio
async def test_local_reference_rejects_unit_not_in_source_snapshot():
    with pytest.raises(ValueError, match="authoritative source snapshot"):
        await ManualMealNutritionResolver().resolve_items(
            [
                ManualMealItem(
                    name="Rice",
                    quantity=1,
                    unit="bowl",
                    origin="local",
                    food_reference_id=42,
                )
            ],
            _References(),
            contract_version=2,
        )


@pytest.mark.asyncio
async def test_unverified_reference_fails_closed():
    class _Unverified(_References):
        async def get_nutrition_projection(self, food_reference_id):
            return _reference(is_verified=False)

    with pytest.raises(NutritionIntegrityError, match="unverified_reference"):
        await ManualMealNutritionResolver().resolve_items(
            [
                ManualMealItem(
                    name="Rice",
                    quantity=100,
                    unit="g",
                    origin="local",
                    food_reference_id=42,
                )
            ],
            _Unverified(),
            contract_version=2,
        )


@pytest.mark.asyncio
async def test_provider_resolution_requires_shared_budget():
    provider = SimpleNamespace(
        get_food_details=AsyncMock(
            return_value={
                "food_id": "provider-1",
                "food_name": "Rice",
                "protein_100g": 2.7,
                "carbs_100g": 28.0,
                "fat_100g": 0.3,
                "calories_100g": 124.7,
            }
        )
    )
    with pytest.raises(NutritionIntegrityError, match="provider_budget_unavailable"):
        await ManualMealNutritionResolver(provider=provider).resolve_items(
            [
                ManualMealItem(
                    name="Rice",
                    quantity=100,
                    unit="g",
                    origin="provider",
                    source_namespace="fatsecret",
                    source_food_id="provider-1",
                )
            ],
            _References(),
            contract_version=2,
        )
    provider.get_food_details.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_resolution_uses_shared_budget_and_deadline():
    provider = SimpleNamespace(
        get_food_details=AsyncMock(
            return_value={
                "food_id": "provider-1",
                "food_name": "Rice",
                "protein_100g": 2.7,
                "carbs_100g": 28.0,
                "fat_100g": 0.3,
                "calories_100g": 124.7,
            }
        )
    )

    class _Budget:
        async def acquire(self, namespace, limit):
            assert namespace == "fatsecret"
            assert limit == 10
            return True

    resolved = await ManualMealNutritionResolver(
        provider=provider,
        provider_budget=_Budget(),
        provider_rpm=10,
        provider_timeout_seconds=1,
    ).resolve_items(
        [
            ManualMealItem(
                name="Rice",
                quantity=100,
                unit="g",
                origin="provider",
                source_namespace="fatsecret",
                source_food_id="provider-1",
            )
        ],
        _References(),
        contract_version=2,
    )

    assert resolved[0].source_snapshot["source_food_id"] == "provider-1"
    provider.get_food_details.assert_awaited_once_with("provider-1")
