"""Presentation localization for food-label scan display names."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from src.app.services.food_display_name import needs_display_localization
from src.app.services.food_name_localizer import (
    translate_food_texts,
    translated_values,
)
from src.domain.model.nutrition import FoodItem, Nutrition
from src.domain.model.translation_result import TranslationOutcome

__all__ = ["localize_food_label_display"]


async def localize_food_label_display(
    *,
    nutrition: Nutrition,
    metadata: dict[str, Any] | None,
    language: str,
    translation_service: Any | None,
) -> tuple[Nutrition, dict[str, Any] | None]:
    """Localize leftover English food-label names for the request language.

    Printed non-English product names stay as-is. English leftovers are
    translated for presentation and persisted on the meal so Today's Meals
    and meal detail can trust the stored display names (same contract as
    scanner meals).
    """

    normalized = (language or "en").strip().lower()
    if normalized == "en" or translation_service is None:
        return nutrition, metadata

    food_items = list(getattr(nutrition, "food_items", None) or [])
    metadata_dict = dict(metadata) if isinstance(metadata, dict) else None
    product_name = None
    if metadata_dict is not None:
        raw_product_name = metadata_dict.get("product_name")
        if isinstance(raw_product_name, str):
            product_name = raw_product_name

    originals: list[str] = []
    if product_name and needs_display_localization(product_name, normalized):
        originals.append(product_name)
    for item in food_items:
        name = getattr(item, "name", None)
        if (
            isinstance(name, str)
            and name.strip()
            and needs_display_localization(name, normalized)
            and name not in originals
        ):
            originals.append(name)

    if not originals:
        return nutrition, metadata_dict

    result = await translate_food_texts(
        originals,
        target_language=normalized,
        translation_service=translation_service,
    )
    if result.outcome not in {
        TranslationOutcome.TRANSLATED,
        TranslationOutcome.PARTIAL,
    }:
        return nutrition, metadata_dict

    localized_by_source = dict(
        zip(originals, translated_values(originals, result), strict=False)
    )

    if metadata_dict is not None and product_name in localized_by_source:
        localized_product = localized_by_source[product_name]
        if isinstance(localized_product, str) and localized_product.strip():
            metadata_dict["product_name"] = localized_product.strip()

    localized_items: list[FoodItem] = []
    for item in food_items:
        name = getattr(item, "name", None)
        replacement = localized_by_source.get(name) if isinstance(name, str) else None
        if isinstance(replacement, str) and replacement.strip():
            localized_items.append(replace(item, name=replacement.strip()))
        else:
            localized_items.append(item)

    return replace(nutrition, food_items=localized_items), metadata_dict
