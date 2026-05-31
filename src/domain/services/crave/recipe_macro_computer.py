from dataclasses import dataclass
from typing import Any


@dataclass
class ComputedMacros:
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    coverage: float


def derive_calories(
    protein_g: float, carbs_g: float, fat_g: float, fiber_g: float
) -> int:
    net_carbs = max(carbs_g - fiber_g, 0.0)
    return round(protein_g * 4 + net_carbs * 4 + fiber_g * 2 + fat_g * 9)


class RecipeMacroComputer:
    """Compute verified recipe macros from per-100g ingredient references."""

    def __init__(self, resolver: Any, min_coverage: float = 0.8) -> None:
        self._resolver = resolver
        self._min_coverage = min_coverage

    async def compute(self, ingredients: list[dict[str, Any]]) -> ComputedMacros | None:
        if not ingredients:
            return None

        protein = carbs = fat = fiber = 0.0
        resolved = 0
        for ingredient in ingredients:
            name = ingredient.get("name")
            grams = float(ingredient.get("grams") or 0)
            if not name or grams <= 0:
                continue

            macros = await self._resolver.resolve(name)
            if macros is None:
                continue

            factor = grams / 100.0
            protein += macros.protein * factor
            carbs += macros.carbs * factor
            fat += macros.fat * factor
            fiber += getattr(macros, "fiber", 0.0) * factor
            resolved += 1

        coverage = resolved / len(ingredients)
        if coverage < self._min_coverage:
            return None

        protein = round(protein, 1)
        carbs = round(carbs, 1)
        fat = round(fat, 1)
        fiber = round(fiber, 1)
        return ComputedMacros(
            calories=derive_calories(protein, carbs, fat, fiber),
            protein_g=protein,
            carbs_g=carbs,
            fat_g=fat,
            fiber_g=fiber,
            coverage=coverage,
        )
