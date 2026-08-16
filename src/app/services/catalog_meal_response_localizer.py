"""Request-language localization for catalog meal response projections."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import replace
from typing import Any, Protocol

from src.app.services.food_name_localizer import translate_for_presentation
from src.domain.model.meal_recommendation import (
    CatalogMeal,
    PersistedMealRecommendationCandidate,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)
from src.domain.model.translation_result import TranslationOutcome

logger = logging.getLogger(__name__)


class TextTranslationService(Protocol):
    """Minimal translation dependency needed by catalog response localization."""

    async def translate_texts(self, texts: list[str], *args: str) -> Any: ...


async def localize_meal_recommendation_plan(
    plan: PersistedMealRecommendationPlan,
    *,
    language: str,
    translation_service: TextTranslationService | None,
) -> PersistedMealRecommendationPlan:
    """Return a localized presentation copy of a recommendation plan."""

    if language == "en" or translation_service is None:
        return plan

    meals = [
        meal
        for slot in plan.slots
        for meal in _slot_catalog_meals(slot)
    ]
    localized_meals = await _localized_meals(
        meals,
        language=language,
        translation_service=translation_service,
    )
    if localized_meals is None:
        return plan

    return replace(
        plan,
        slots=tuple(
            _replace_slot_catalog_meals(slot, localized_meals) for slot in plan.slots
        ),
    )


async def localize_meal_recommendation_slot(
    slot: PersistedMealRecommendationSlot,
    *,
    language: str,
    translation_service: TextTranslationService | None,
) -> PersistedMealRecommendationSlot:
    """Return a localized presentation copy of one recommendation slot."""

    if language == "en" or translation_service is None:
        return slot

    localized_meals = await _localized_meals(
        list(_slot_catalog_meals(slot)),
        language=language,
        translation_service=translation_service,
    )
    if localized_meals is None:
        return slot

    return _replace_slot_catalog_meals(slot, localized_meals)


def _slot_catalog_meals(slot: PersistedMealRecommendationSlot) -> tuple[CatalogMeal, ...]:
    candidates = (slot.selected, *slot.alternatives)
    return tuple(
        candidate.catalog_meal
        for candidate in candidates
        if candidate is not None and candidate.catalog_meal is not None
    )


async def _localized_meals(
    meals: list[CatalogMeal],
    *,
    language: str,
    translation_service: TextTranslationService,
) -> dict[str, CatalogMeal] | None:
    unique_meals = {meal.id: meal for meal in meals}
    texts = _unique_display_texts(unique_meals.values())
    if not texts:
        return dict(unique_meals)

    try:
        result = await translate_for_presentation(translation_service, texts, language)
    except Exception as exc:
        logger.warning(
            "catalog response translation failed language=%s error_type=%s",
            language,
            type(exc).__name__,
        )
        return None

    if result.outcome is TranslationOutcome.UNAVAILABLE:
        return None

    translations = {
        text: result.items[index] if index < len(result.items) else text
        for index, text in enumerate(texts)
    }
    return {
        meal_id: _replace_meal_display_text(meal, translations)
        for meal_id, meal in unique_meals.items()
    }


def _unique_display_texts(meals: Iterable[CatalogMeal]) -> list[str]:
    texts: list[str] = []
    for meal in meals:
        _append_unique(texts, meal.name)
        _append_unique(texts, meal.cuisine)
        if meal.description:
            _append_unique(texts, meal.description)
        for ingredient in meal.ingredients:
            _append_unique(texts, ingredient.display_name)
    return texts


def _append_unique(texts: list[str], value: str) -> None:
    if value and value not in texts:
        texts.append(value)


def _replace_meal_display_text(
    meal: CatalogMeal,
    translations: dict[str, str],
) -> CatalogMeal:
    return replace(
        meal,
        name=translations.get(meal.name, meal.name),
        cuisine=translations.get(meal.cuisine, meal.cuisine),
        description=(
            translations.get(meal.description, meal.description)
            if meal.description
            else None
        ),
        ingredients=tuple(
            replace(
                ingredient,
                display_name=translations.get(
                    ingredient.display_name,
                    ingredient.display_name,
                ),
            )
            for ingredient in meal.ingredients
        ),
    )


def _replace_slot_catalog_meals(
    slot: PersistedMealRecommendationSlot,
    localized_meals: dict[str, CatalogMeal],
) -> PersistedMealRecommendationSlot:
    return replace(
        slot,
        selected=(
            _replace_candidate_catalog_meal(slot.selected, localized_meals)
            if slot.selected is not None
            else None
        ),
        alternatives=tuple(
            _replace_candidate_catalog_meal(candidate, localized_meals)
            for candidate in slot.alternatives
        ),
    )


def _replace_candidate_catalog_meal(
    candidate: PersistedMealRecommendationCandidate,
    localized_meals: dict[str, CatalogMeal],
) -> PersistedMealRecommendationCandidate:
    if candidate.catalog_meal is None:
        return candidate
    return replace(
        candidate,
        catalog_meal=localized_meals.get(candidate.catalog_meal.id, candidate.catalog_meal),
    )
