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
