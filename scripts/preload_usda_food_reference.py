"""USDA FoodData Central preload helpers for food_reference."""

from typing import Any

_NUTRIENT_MAP = {
    "Protein": "protein_100g",
    "Carbohydrate, by difference": "carbs_100g",
    "Total lipid (fat)": "fat_100g",
    "Fiber, total dietary": "fiber_100g",
}


def usda_row_to_food_reference(row: dict[str, Any]) -> dict[str, Any] | None:
    name = row.get("description")
    if not name:
        return None

    macros = {
        "protein_100g": 0.0,
        "carbs_100g": 0.0,
        "fat_100g": 0.0,
        "fiber_100g": 0.0,
    }
    for nutrient in row.get("foodNutrients", []):
        key = _NUTRIENT_MAP.get(nutrient.get("nutrientName"))
        if key:
            macros[key] = float(nutrient.get("value") or 0.0)

    from src.domain.services.meal_suggestion.ingredient_name_normalizer import (
        normalize_food_name,
    )

    return {
        "name": name,
        "name_normalized": normalize_food_name(name),
        **macros,
        "source": "usda",
        "is_verified": True,
        "external_id": str(row.get("fdcId", "")),
    }


def main(path: str) -> None:
    raise NotImplementedError(
        "Batch preload wiring is intentionally environment-specific; "
        "use usda_row_to_food_reference with the FoodReferenceRepository."
    )


if __name__ == "__main__":
    import sys

    main(sys.argv[1])
