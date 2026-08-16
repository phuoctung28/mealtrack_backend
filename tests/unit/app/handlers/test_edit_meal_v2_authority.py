from types import SimpleNamespace

import pytest

from src.app.commands.meal import FoodItemChange
from src.app.handlers.command_handlers.edit_meal_command_handler import (
    EditMealCommandHandler,
)
from src.domain.model.nutrition import FoodItem, Macros


class _References:
    async def get_nutrition_projection(self, food_reference_id):
        return SimpleNamespace(
            id=food_reference_id,
            name="Canonical rice",
            source="catalog",
            is_verified=True,
            protein_100g=2.7,
            carbs_100g=28.0,
            fat_100g=0.3,
            fiber_100g=0.4,
            sugar_100g=0.1,
            servings=[],
        )


@pytest.mark.asyncio
async def test_v2_source_replacement_is_resolved_before_edit_strategy():
    current = FoodItem(
        id="item-1",
        name="Old rice",
        quantity=100,
        unit="g",
        macros=Macros(protein=1, carbs=1, fat=1),
    )
    change = FoodItemChange(
        action="update",
        id="item-1",
        origin="local",
        food_reference_id=42,
        quantity=100,
        unit="g",
    )
    handler = EditMealCommandHandler(uow=None)

    prepared = await handler._prepare_v2_changes(
        [current], [change], SimpleNamespace(food_references=_References())
    )

    assert prepared[0].name == "Canonical rice"
    assert prepared[0].custom_nutrition.protein_per_100g == pytest.approx(2.7)
    assert prepared[0].source_snapshot["basis"] == "100g"


@pytest.mark.asyncio
async def test_v2_source_replacement_canonicalizes_arbitrary_unit_before_strategy():
    current = FoodItem(
        id="item-1",
        name="Old rice",
        quantity=100,
        unit="g",
        macros=Macros(protein=1, carbs=1, fat=1),
    )
    change = FoodItemChange(
        action="update",
        id="item-1",
        origin="local",
        food_reference_id=42,
        quantity=100,
        unit="g private-text",
    )
    handler = EditMealCommandHandler(uow=None)

    prepared = await handler._prepare_v2_changes(
        [current], [change], SimpleNamespace(food_references=_References())
    )
    updated = await handler._apply_food_item_changes([current], prepared)

    assert prepared[0].quantity == pytest.approx(100)
    assert prepared[0].unit == "g"
    assert updated[0].quantity == pytest.approx(100)
    assert updated[0].unit == "g"
    assert updated[0].macros.protein == pytest.approx(2.7)


@pytest.mark.asyncio
async def test_v2_quantity_update_canonicalizes_arbitrary_unit_before_strategy():
    current = FoodItem(
        id="item-1",
        name="Canonical rice",
        quantity=1,
        unit="cup",
        macros=Macros(protein=4.266, carbs=44.24, fat=0.474),
        nutrition_contract_version="2",
        source_snapshot={
            "basis": "100g",
            "protein_per_100g": 2.7,
            "carbs_per_100g": 28.0,
            "fat_per_100g": 0.3,
            "fiber_per_100g": 0.4,
            "sugar_per_100g": 0.1,
            "allowed_units": [
                {"unit": "g", "gram_weight": 1.0, "description": "1 g"},
                {"unit": "cup", "gram_weight": 158.0, "description": "cup"},
            ],
        },
    )
    change = FoodItemChange(
        action="update",
        id="item-1",
        quantity=100,
        unit="cup private-text",
    )
    handler = EditMealCommandHandler(uow=None)

    prepared = await handler._prepare_v2_changes(
        [current], [change], SimpleNamespace(food_references=_References())
    )
    updated = await handler._apply_food_item_changes([current], prepared)

    assert prepared[0].quantity == pytest.approx(100)
    assert prepared[0].unit == "g"
    assert updated[0].quantity == pytest.approx(100)
    assert updated[0].unit == "g"
    assert updated[0].macros.protein == pytest.approx(2.7)
