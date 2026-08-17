"""Translation service for meal suggestions."""

import asyncio
import logging
from dataclasses import replace as dataclasses_replace

from src.domain.model.meal_suggestion import MealSuggestion
from src.domain.services.translation.text_translation_service import (
    TextTranslationService,
)

logger = logging.getLogger(__name__)


class SuggestionTranslationService:
    """
    Translates MealSuggestion objects.

    Uses TextTranslationService for actual provider calls.
    Adds suggestion-specific dataclass handling on top.
    """

    def __init__(self, text_translation_service: TextTranslationService) -> None:
        self._text_service = text_translation_service

    # ------------------------------------------------------------------
    # Public interface (matches TranslationService)
    # ------------------------------------------------------------------

    async def translate_meal_suggestion(
        self, suggestion: MealSuggestion, target_language: str
    ) -> MealSuggestion:
        """Translate a single suggestion; returns original on failure."""
        if target_language == "en":
            return suggestion
        try:
            return await self._translate_one(suggestion, target_language)
        except Exception as exc:
            logger.warning(
                "Suggestion translation failed for suggestion=%s lang=%s: %s",
                suggestion.id,
                target_language,
                exc,
            )
            return suggestion

    async def translate_meal_suggestions_batch(
        self, suggestions: list[MealSuggestion], target_language: str
    ) -> list[MealSuggestion]:
        """Translate all suggestions concurrently; falls back per-item on failure."""
        if target_language == "en" or not suggestions:
            return suggestions

        results = await asyncio.gather(
            *[self._translate_one(s, target_language) for s in suggestions],
            return_exceptions=True,
        )

        translated = []
        for original, result in zip(suggestions, results, strict=True):
            if isinstance(result, Exception):
                logger.warning(
                    "Suggestion translation failed for suggestion=%s: %s",
                    original.id,
                    result,
                )
                translated.append(original)
            else:
                translated.append(result)
        return translated

    async def translate_names(
        self, names: list[str], target_language: str
    ) -> list[str]:
        """Translate a list of meal names. Returns originals on failure."""
        if target_language == "en" or not names:
            return names
        try:
            return await self._text_service.translate_texts(names, target_language)
        except Exception as exc:
            logger.warning("translate_names failed: %s", exc)
            return names

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _translate_one(
        self, suggestion: MealSuggestion, target_language: str
    ) -> MealSuggestion:
        """
        Build one flat string list, call the provider once, then reconstruct the
        MealSuggestion dataclass with translated values.
        """
        # Layout: [meal_name, description, *ingredient_names, *step_instructions]
        strings: list[str] = [suggestion.meal_name, suggestion.description or ""]
        n_ingredients = len(suggestion.ingredients)

        strings.extend(ing.name for ing in suggestion.ingredients)
        strings.extend(step.instruction for step in suggestion.recipe_steps)

        translated = await self._text_service.translate_texts(strings, target_language)

        # Pad in case a provider returns fewer items than requested.
        while len(translated) < len(strings):
            translated.append(strings[len(translated)])

        idx = 0
        translated_name = translated[idx]
        idx += 1
        translated_description = translated[idx]
        idx += 1

        translated_ingredients = [
            dataclasses_replace(ing, name=translated[idx + i])
            for i, ing in enumerate(suggestion.ingredients)
        ]
        idx += n_ingredients

        translated_steps = [
            dataclasses_replace(step, instruction=translated[idx + i])
            for i, step in enumerate(suggestion.recipe_steps)
        ]

        return dataclasses_replace(
            suggestion,
            meal_name=translated_name,
            description=translated_description,
            ingredients=translated_ingredients,
            recipe_steps=translated_steps,
        )
