"""Shared food-reference projection and child-row helpers."""

from typing import Any

from src.infra.database.models.food_reference_model import FoodReferenceModel
from src.infra.database.models.food_reference_nutrient import FoodReferenceNutrientModel
from src.infra.database.models.food_reference_serving_size import (
    FoodReferenceServingSizeModel,
)

FOOD_REFERENCE_SEED_COLUMNS = {
    "barcode",
    "name",
    "name_vi",
    "brand",
    "category",
    "region",
    "fdc_id",
    "protein_100g",
    "carbs_100g",
    "fat_100g",
    "fiber_100g",
    "sugar_100g",
    "extra_nutrients",
    "serving_sizes",
    "density",
    "serving_size",
    "source",
    "is_verified",
    "image_url",
}


def food_reference_model_to_dict(model: FoodReferenceModel) -> dict[str, Any]:
    """Convert a food reference ORM row to its API/service dictionary shape."""
    return {
        "id": model.id,
        "barcode": model.barcode,
        "name": model.name,
        "name_vi": model.name_vi,
        "brand": model.brand,
        "category": model.category,
        "region": model.region,
        "fdc_id": model.fdc_id,
        "protein_100g": model.protein_100g,
        "carbs_100g": model.carbs_100g,
        "fat_100g": model.fat_100g,
        "fiber_100g": model.fiber_100g,
        "sugar_100g": model.sugar_100g,
        "serving_sizes": food_reference_serving_sizes_to_dict(model),
        "density": model.density,
        "serving_size": model.serving_size,
        "extra_nutrients": food_reference_nutrients_to_dict(model),
        "source": model.source,
        "is_verified": model.is_verified,
        "image_url": model.image_url,
    }


def build_food_reference_serving_rows(
    raw: Any,
) -> list[FoodReferenceServingSizeModel]:
    if not isinstance(raw, list):
        return []
    rows: list[FoodReferenceServingSizeModel] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("label") or "").strip()
        if not name:
            continue
        rows.append(
            FoodReferenceServingSizeModel(
                name=name[:100],
                grams=as_optional_float(item.get("grams")),
                milliliters=as_optional_float(
                    item.get("milliliters") or item.get("ml")
                ),
                is_default=bool(item.get("is_default", idx == 0)),
                position=idx,
            )
        )
    return rows


def build_food_reference_nutrient_rows(raw: Any) -> list[FoodReferenceNutrientModel]:
    if not isinstance(raw, dict):
        return []
    rows: list[FoodReferenceNutrientModel] = []
    for key, value in sorted(raw.items()):
        if isinstance(value, dict):
            amount = as_optional_float(value.get("amount"))
            unit = value.get("unit")
        else:
            amount = as_optional_float(value)
            unit = None
        if amount is None:
            continue
        rows.append(
            FoodReferenceNutrientModel(
                nutrient_key=str(key)[:100],
                amount=amount,
                unit=str(unit)[:32] if unit else None,
            )
        )
    return rows


def food_reference_serving_sizes_to_dict(model: FoodReferenceModel) -> Any:
    rows = getattr(model, "serving_size_rows", None)
    if not rows:
        return model.serving_sizes
    return [
        {
            "name": row.name,
            "grams": row.grams,
            "milliliters": row.milliliters,
            "is_default": row.is_default,
        }
        for row in rows
    ]


def food_reference_nutrients_to_dict(model: FoodReferenceModel) -> Any:
    rows = getattr(model, "nutrient_rows", None)
    if not rows:
        return model.extra_nutrients
    raw = model.extra_nutrients if isinstance(model.extra_nutrients, dict) else {}
    projected = dict(raw)
    for row in rows:
        legacy_value = raw.get(row.nutrient_key)
        if isinstance(legacy_value, dict):
            projected[row.nutrient_key] = {
                **legacy_value,
                "amount": row.amount,
                "unit": row.unit,
            }
        elif row.nutrient_key in raw:
            projected[row.nutrient_key] = row.amount
        else:
            projected[row.nutrient_key] = {
                "amount": row.amount,
                "unit": row.unit,
            }
    return projected


def as_optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
