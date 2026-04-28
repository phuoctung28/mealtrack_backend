"""
Translation service for food search queries and results.
Translates user queries to English for FatSecret lookup,
then translates food names back to user's language.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.prompts.prompt_constants import LANGUAGE_NAMES

logger = logging.getLogger(__name__)


class FoodSearchTranslationService:
    """Translate food search queries and result names via Gemini."""

    def __init__(self, generation_service: MealGenerationServicePort) -> None:
        self._generation_service = generation_service

    async def translate_query(self, query: str, source_language: str) -> Optional[str]:
        """Translate a food search query to English.
        Returns None on failure (caller should use original query).
        """
        if source_language == "en" or not query.strip():
            return query

        lang_name = LANGUAGE_NAMES.get(source_language, source_language)
        prompt = (
            f"Translate this {lang_name} food search query to English. "
            f'Return ONLY a JSON object {{"translation": "..."}}.\n'
            f'Query: "{query}"'
        )
        system_message = "Food terminology translator. Return ONLY valid JSON."

        try:
            result = await asyncio.to_thread(
                self._generation_service.generate_meal_plan,
                prompt,
                system_message,
                response_type="json",
                max_tokens=256,
            )
            translated = result.get("translation", "")
            if isinstance(translated, str) and translated.strip():
                return translated.strip()
            # Fallback: try first string value in response
            for v in result.values():
                if isinstance(v, str) and v.strip():
                    return v.strip()
            return None
        except Exception as e:
            logger.warning(f"Query translation failed: {e}")
            return None

    async def translate_food_names(
        self, foods: List[Dict[str, Any]], target_language: str
    ) -> List[Dict[str, Any]]:
        """Translate food name/description fields to target language.
        Modifies dicts in-place and returns same list.
        """
        if target_language == "en" or not foods:
            return foods

        # Extract unique names to translate
        names: List[str] = []
        for food in foods:
            name = food.get("description") or food.get("name", "")
            if name and name not in names:
                names.append(name)

        if not names:
            return foods

        lang_name = LANGUAGE_NAMES.get(target_language, target_language)
        n = len(names)
        prompt = (
            f"Translate these {n} English food names to {lang_name}. "
            f"Keep brand names, units, numbers unchanged. "
            f"Return EXACTLY {n} translations in same order.\n"
            f"Input:\n{json.dumps(names, ensure_ascii=False)}\n"
            f'Output: ONLY JSON {{"translations":[...{n} items...]}}'
        )
        system_message = (
            f"Professional {lang_name} food name translator. "
            f"Return ONLY valid JSON."
        )

        try:
            result = await asyncio.to_thread(
                self._generation_service.generate_meal_plan,
                prompt,
                system_message,
                response_type="json",
                max_tokens=2048,
            )
            translations: List[str] = result.get("translations", [])

            # Pad missing entries with originals
            if len(translations) < n:
                logger.warning(f"Got {len(translations)}/{n} translations, padding")
                translations.extend(names[len(translations) :])

            # Build lookup
            name_map = dict(zip(names, translations))

            # Apply to foods
            for food in foods:
                original = food.get("description") or food.get("name", "")
                translated = name_map.get(original)
                if translated:
                    if "description" in food:
                        food["description_original"] = original
                        food["description"] = translated
                    if "name" in food:
                        food["name_original"] = original
                        food["name"] = translated

            return foods
        except Exception as e:
            logger.warning(f"Food name translation failed: {e}")
            return foods
