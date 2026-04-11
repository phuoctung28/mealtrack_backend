"""
DeepL-backed translation service for meal suggestions.

Drop-in replacement for the Gemini-based TranslationService.
Translates meal_name, description, ingredient names, and recipe step
instructions using a single batched DeepL API call per suggestion.
"""
import asyncio
import logging
from dataclasses import replace as dataclasses_replace
from typing import List

from src.domain.model.meal_suggestion import MealSuggestion
from src.domain.ports.deepl_translation_port import DeepLTranslationPort

logger = logging.getLogger(__name__)


class DeepLSuggestionTranslationService:
    """
    Translates MealSuggestion objects via DeepL.

    Compatible with the SuggestionOrchestrationService interface —
    exposes the same two public methods as the Gemini TranslationService:
      • translate_meal_suggestion()
      • translate_meal_suggestions_batch()

    For each suggestion the translatable strings are batched into ONE DeepL
    API call in this order:
      [meal_name, description, *ingredient_names, *step_instructions]

    Multiple suggestions are translated concurrently with asyncio.gather.
    On any failure the original (English) suggestion is returned so the
    response is never blocked.
    """

    def __init__(self, deepl_port: DeepLTranslationPort) -> None:
        self._deepl = deepl_port

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
                "DeepL translation failed for suggestion=%s lang=%s: %s",
                suggestion.id, target_language, exc
            )
            return suggestion

    async def translate_meal_suggestions_batch(
        self, suggestions: List[MealSuggestion], target_language: str
    ) -> List[MealSuggestion]:
        """Translate all suggestions concurrently; falls back per-item on failure."""
        if target_language == "en" or not suggestions:
            return suggestions

        results = await asyncio.gather(
            *[self._translate_one(s, target_language) for s in suggestions],
            return_exceptions=True,
        )

        translated = []
        for original, result in zip(suggestions, results):
            if isinstance(result, Exception):
                logger.warning(
                    "DeepL translation failed for suggestion=%s: %s",
                    original.id, result
                )
                translated.append(original)
            else:
                translated.append(result)
        return translated

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _translate_one(
        self, suggestion: MealSuggestion, target_language: str
    ) -> MealSuggestion:
        """
        Build one flat string list, call DeepL once, then reconstruct the
        MealSuggestion dataclass with translated values.
        """
        # Layout: [meal_name, description, *ingredient_names, *step_instructions]
        strings: List[str] = [suggestion.meal_name, suggestion.description or ""]
        n_ingredients = len(suggestion.ingredients)
        n_steps = len(suggestion.recipe_steps)

        strings.extend(ing.name for ing in suggestion.ingredients)
        strings.extend(step.instruction for step in suggestion.recipe_steps)

        translated = await self._deepl.translate_texts(strings, target_language)

        # Pad in case DeepL returns fewer items than requested.
        while len(translated) < len(strings):
            translated.append(strings[len(translated)])

        idx = 0
        translated_name = translated[idx]; idx += 1
        translated_description = translated[idx]; idx += 1

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
