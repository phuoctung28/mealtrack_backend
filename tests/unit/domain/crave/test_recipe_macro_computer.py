import pytest

from src.domain.services.crave.recipe_macro_computer import RecipeMacroComputer
from src.domain.services.meal_suggestion.ingredient_nutrition_resolver import (
    PerHundredGramsMacros,
)


class FakeResolver:
    def __init__(self, table):
        self.table = table

    async def resolve(self, name):
        return self.table.get(name)


@pytest.mark.asyncio
async def test_computes_macros_by_scaling_per_100g_by_grams():
    resolver = FakeResolver(
        {
            "salmon": PerHundredGramsMacros(
                protein=20.0, carbs=0.0, fat=13.0, fiber=0.0
            ),
            "rice": PerHundredGramsMacros(protein=2.7, carbs=28.0, fat=0.3, fiber=0.4),
        }
    )

    result = await RecipeMacroComputer(resolver).compute(
        [
            {"name": "salmon", "grams": 150},
            {"name": "rice", "grams": 200},
        ]
    )

    assert result is not None
    assert round(result.protein_g, 1) == 35.4
    assert round(result.carbs_g, 1) == 56.0
    assert round(result.fat_g, 1) == 20.1
    assert result.calories == round(35.4 * 4 + (56.0 - 0.8) * 4 + 0.8 * 2 + 20.1 * 9)
    assert result.coverage == 1.0


@pytest.mark.asyncio
async def test_returns_none_when_coverage_below_threshold():
    resolver = FakeResolver(
        {"salmon": PerHundredGramsMacros(protein=20.0, carbs=0.0, fat=13.0, fiber=0.0)}
    )

    result = await RecipeMacroComputer(resolver, min_coverage=0.8).compute(
        [
            {"name": "salmon", "grams": 150},
            {"name": "mystery-x", "grams": 100},
            {"name": "mystery-y", "grams": 100},
        ]
    )

    assert result is None
