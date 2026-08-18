"""Meal calorie helpers for source-specific display and summary totals."""

from typing import Any

from src.domain.model.nutrition.macros import Macros


def effective_meal_calories(meal: Any) -> float:
    """Return calories users expect for a meal.

    Food-label scans should match the printed label calories. Other meal
    sources keep the canonical macro-derived value, unless a meal-level
    override is set or ingredient calorie overrides require summing items.
    """
    from src.domain.model.nutrition.nutrition import Nutrition, NutritionOverride

    nutrition = getattr(meal, "nutrition", None)
    if nutrition is None:
        return 0.0

    override = getattr(nutrition, "nutrition_override", None)
    if isinstance(override, NutritionOverride):
        return float(override.calories)

    if getattr(meal, "source", None) == "food_label":
        metadata = getattr(meal, "food_label_metadata", None)
        label_calories = _food_label_calories(metadata)
        if label_calories is not None:
            item = (getattr(nutrition, "food_items", None) or [None])[0]
            return _scaled_label_calories(label_calories, item, metadata)

    # Real Nutrition VOs may include per-item calorie overrides in .calories.
    if isinstance(nutrition, Nutrition):
        return float(nutrition.calories)

    return _macro_calories(getattr(nutrition, "macros", None))


def effective_food_item_calories(
    item: Any,
    *,
    meal_source: str | None = None,
    food_label_metadata: dict[str, Any] | None = None,
) -> float:
    """Return item calories, preserving printed calories for label scans."""
    if meal_source == "food_label":
        label_calories = _food_label_calories(food_label_metadata)
        if label_calories is not None:
            return _scaled_label_calories(label_calories, item, food_label_metadata)

    return float(getattr(item, "calories", 0.0) or 0.0)


def _macro_calories(macros: Any) -> float:
    if macros is None:
        return 0.0

    protein = _safe_number(getattr(macros, "protein", 0.0))
    carbs = _safe_number(getattr(macros, "carbs", 0.0))
    fat = _safe_number(getattr(macros, "fat", 0.0))
    fiber = _safe_number(getattr(macros, "fiber", 0.0))
    return round(Macros.raw_total_calories(protein, carbs, fat, fiber), 1)


def _safe_number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _food_label_calories(metadata: dict[str, Any] | None) -> float | None:
    if not isinstance(metadata, dict):
        return None

    value = metadata.get("label_calories_per_serving")
    if value is None:
        return None

    try:
        calories = float(value)
    except (TypeError, ValueError):
        return None

    return calories if calories >= 0 else None


def _scaled_label_calories(
    label_calories: float,
    item: Any,
    metadata: dict[str, Any] | None,
) -> float:
    serving_size = metadata.get("serving_size") if isinstance(metadata, dict) else None
    serving_grams = None
    if isinstance(serving_size, dict):
        try:
            serving_grams = float(serving_size.get("grams") or 0)
        except (TypeError, ValueError):
            serving_grams = None

    quantity = getattr(item, "quantity", None)
    unit = str(getattr(item, "unit", "") or "").strip().lower()
    if item is None:
        return round(label_calories, 1)

    try:
        quantity_value = float(quantity)
    except (TypeError, ValueError):
        return round(label_calories, 1)

    if quantity_value <= 0:
        return round(label_calories, 1)

    if unit in {"serving", "servings"}:
        return round(label_calories * quantity_value, 1)

    if unit in {"package", "packages"}:
        servings_per_package = None
        if isinstance(metadata, dict):
            try:
                servings_per_package = float(metadata.get("servings_per_package") or 0)
            except (TypeError, ValueError):
                servings_per_package = None
        if servings_per_package and servings_per_package > 0:
            return round(label_calories * quantity_value * servings_per_package, 1)
        return round(label_calories, 1)

    if unit not in {"g", "gram", "grams"}:
        return round(label_calories, 1)

    if not serving_grams or serving_grams <= 0:
        return round(label_calories, 1)

    return round(label_calories * (quantity_value / serving_grams), 1)
