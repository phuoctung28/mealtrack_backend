from typing import Any


def validate_barcode_nutrition(payload: dict[str, Any]) -> dict[str, Any]:
    """Clamp per-100g barcode nutrition without meal-level macro assumptions."""
    result = dict(payload)
    protein = _non_negative(result.get("protein_100g"))
    carbs = _non_negative(result.get("carbs_100g"))
    fat = _non_negative(result.get("fat_100g"))
    fiber = _non_negative(result.get("fiber_100g"))
    sugar = _non_negative(result.get("sugar_100g"))

    result["protein_100g"] = protein
    result["carbs_100g"] = carbs
    result["fat_100g"] = fat
    result["fiber_100g"] = fiber
    result["sugar_100g"] = sugar
    result["calories_100g"] = _derive_calories(protein, carbs, fat, fiber)
    return result


def _non_negative(value: Any) -> float:
    try:
        return max(0.0, float(value or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _derive_calories(protein: float, carbs: float, fat: float, fiber: float) -> float:
    net_carbs = max(0.0, carbs - fiber)
    return round(protein * 4 + net_carbs * 4 + fiber * 2 + fat * 9, 1)

