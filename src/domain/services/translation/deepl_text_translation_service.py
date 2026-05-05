"""
DeepL-backed text translation service.

Provides simple text translation for food search, ingredient recognition,
barcode lookup, and meal text parsing flows.
"""

import logging
from typing import Any, Dict, List

from src.domain.ports.deepl_translation_port import DeepLTranslationPort

logger = logging.getLogger(__name__)


class DeepLTextTranslationService:
    """
    Translates text via DeepL for various flows.

    On any error, returns original content and logs a warning.
    Never blocks the main flow due to translation failure.
    """

    def __init__(self, deepl_port: DeepLTranslationPort) -> None:
        self._deepl = deepl_port

    async def translate_texts(self, texts: List[str], target_lang: str) -> List[str]:
        """Translate texts from English to target language."""
        if not texts or target_lang == "en":
            return list(texts) if texts else []

        try:
            return await self._deepl.translate_texts(texts, target_lang)
        except Exception as exc:
            logger.warning(
                "DeepL translate_texts failed (lang=%s): %s", target_lang, exc
            )
            return list(texts)

    async def translate_to_english(
        self, texts: List[str], source_lang: str
    ) -> List[str]:
        """Translate texts from source language to English."""
        if not texts or source_lang == "en":
            return list(texts) if texts else []

        try:
            return await self._deepl.translate_to_english(texts, source_lang)
        except Exception as exc:
            logger.warning(
                "DeepL translate_to_english failed (lang=%s): %s", source_lang, exc
            )
            return list(texts)

    async def translate_food_names(
        self, foods: List[Dict[str, Any]], target_lang: str
    ) -> List[Dict[str, Any]]:
        """
        Translate food name/description fields to target language.
        Modifies dicts in-place, preserving originals as name_original/description_original.
        """
        if not foods or target_lang == "en":
            return foods

        # Extract unique names to translate
        names: List[str] = []
        for food in foods:
            name = food.get("description") or food.get("name", "")
            if name and name not in names:
                names.append(name)

        if not names:
            return foods

        try:
            translated = await self._deepl.translate_texts(names, target_lang)

            # Pad if DeepL returns fewer items
            while len(translated) < len(names):
                translated.append(names[len(translated)])

            # Build lookup
            name_map = dict(zip(names, translated))

            # Apply translations
            for food in foods:
                original = food.get("description") or food.get("name", "")
                translated_name = name_map.get(original)
                if translated_name:
                    if "description" in food:
                        food["description_original"] = original
                        food["description"] = translated_name
                    if "name" in food:
                        food["name_original"] = original
                        food["name"] = translated_name

            return foods

        except Exception as exc:
            logger.warning(
                "DeepL translate_food_names failed (lang=%s): %s", target_lang, exc
            )
            return foods
