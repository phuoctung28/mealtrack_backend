import pytest
from pydantic import ValidationError

from src.api.schemas.request.meal_requests import (
    CreateManualMealFromFoodsRequest,
    EditMealIngredientsRequest,
    NutritionOverrideRequest,
)


def _v2_create_item(**overrides):
    item = {
        "origin": "local",
        "food_reference_id": 42,
        "quantity": 150,
        "unit": "g",
    }
    item.update(overrides)
    return item


def test_v2_reference_item_requires_one_matching_source_identity():
    payload = CreateManualMealFromFoodsRequest(
        dish_name="Rice",
        nutrition_contract_version=2,
        items=[_v2_create_item()],
    )

    assert payload.items[0].origin == "local"


def test_v2_create_accepts_arbitrary_unit_for_backend_normalization():
    payload = CreateManualMealFromFoodsRequest(
        dish_name="Rice",
        nutrition_contract_version=2,
        items=[_v2_create_item(quantity=100, unit="my family bowl")],
    )

    assert payload.items[0].unit == "my family bowl"


def test_v2_custom_item_is_source_less_and_keeps_custom_nutrition():
    payload = CreateManualMealFromFoodsRequest(
        dish_name="Homemade rice",
        nutrition_contract_version=2,
        items=[
            {
                "origin": "custom",
                "name": "Homemade rice",
                "quantity": 100,
                "unit": "g",
                "custom_nutrition": {
                    "protein_per_100g": 2.7,
                    "carbs_per_100g": 28,
                    "fat_per_100g": 0.3,
                },
            }
        ],
    )

    assert payload.items[0].origin == "custom"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "dish_name": "Rice",
            "items": [_v2_create_item()],
        },
        {
            "dish_name": "Rice",
            "nutrition_contract_version": 2,
            "items": [_v2_create_item(origin="local", fdc_id=170000)],
        },
        {
            "dish_name": "Rice",
            "nutrition_contract_version": 2,
            "items": [
                {
                    "origin": "custom",
                    "name": "Rice",
                    "quantity": 100,
                    "unit": "g",
                }
            ],
        },
    ],
)
def test_v2_create_rejects_missing_version_mismatched_ids_and_missing_custom_data(
    payload,
):
    with pytest.raises(ValidationError):
        CreateManualMealFromFoodsRequest.model_validate(payload)


def test_v2_remove_rejects_nutrition_and_source_fields():
    with pytest.raises(ValidationError):
        EditMealIngredientsRequest(
            nutrition_contract_version=2,
            food_item_changes=[
                {
                    "action": "remove",
                    "id": "item-1",
                    "quantity": 100,
                }
            ],
        )


def test_v2_quantity_update_can_inherit_source_without_client_units():
    payload = EditMealIngredientsRequest(
        nutrition_contract_version=2,
        food_item_changes=[
            {"action": "update", "id": "item-1", "quantity": 200, "unit": "g"}
        ],
    )

    assert payload.food_item_changes[0].id == "item-1"


def test_v2_override_requires_explicit_user_intent():
    with pytest.raises(ValidationError):
        EditMealIngredientsRequest(
            nutrition_contract_version=2,
            food_item_changes=[
                {
                    "action": "update",
                    "id": "item-1",
                    "nutrition_override": {
                        "calories": 500,
                        "protein": 20,
                        "carbs": 30,
                        "fat": 15,
                    },
                }
            ],
        )


def test_nutrition_override_rejects_negative_absolute_values():
    with pytest.raises(ValidationError):
        NutritionOverrideRequest(
            calories=500,
            protein=-1,
            carbs=30,
            fat=15,
        )


def test_unknown_nutrition_contract_version_is_rejected():
    with pytest.raises(ValidationError):
        CreateManualMealFromFoodsRequest(
            dish_name="Rice",
            nutrition_contract_version=3,
            items=[{"name": "Rice", "quantity": 100, "unit": "g"}],
        )
