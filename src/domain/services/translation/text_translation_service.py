"""Provider-neutral text translation service."""

import logging
from typing import Any

from src.domain.ports.text_translation_port import TextTranslationPort

logger = logging.getLogger(__name__)


class TextTranslationService:
    """Translate text while degrading safely to the original content."""

    def __init__(self, translation_port: TextTranslationPort) -> None:
        self._translation_port = translation_port

    async def translate_texts(self, texts: list[str], target_lang: str) -> list[str]:
        """Translate English texts to the target language."""
        if not texts or target_lang.lower() == "en":
            return list(texts) if texts else []

        unique = list(dict.fromkeys(text for text in texts if text))
        if not unique:
            return list(texts)

        try:
            translated = await self._translation_port.translate_texts(
                unique, target_lang
            )
            values = list(translated)
            while len(values) < len(unique):
                values.append(unique[len(values)])
            translated_by_source = dict(zip(unique, values, strict=False))
            return [translated_by_source.get(text, text) for text in texts]
        except Exception as exc:
            logger.warning("Text translation failed (lang=%s): %s", target_lang, exc)
            return list(texts)

    async def translate_to_english(
        self, texts: list[str], source_lang: str
    ) -> list[str]:
        """Translate source-language texts to English."""
        if not texts or source_lang.lower() == "en":
            return list(texts) if texts else []

        unique = list(dict.fromkeys(text for text in texts if text))
        if not unique:
            return list(texts)

        try:
            translated = await self._translation_port.translate_to_english(
                unique, source_lang
            )
            values = list(translated)
            while len(values) < len(unique):
                values.append(unique[len(values)])
            translated_by_source = dict(zip(unique, values, strict=False))
            return [translated_by_source.get(text, text) for text in texts]
        except Exception as exc:
            logger.warning(
                "Text translation to English failed (lang=%s): %s", source_lang, exc
            )
            return list(texts)

    async def translate_food_names(
        self, foods: list[dict[str, Any]], target_lang: str
    ) -> list[dict[str, Any]]:
        """Translate food name/description fields in place."""
        if not foods or target_lang.lower() == "en":
            return foods

        names: list[str] = []
        for food in foods:
            name = food.get("description") or food.get("name", "")
            if name and name not in names:
                names.append(name)
        if not names:
            return foods

        try:
            translated = await self._translation_port.translate_texts(
                names, target_lang
            )
            while len(translated) < len(names):
                translated.append(names[len(translated)])
            name_map = dict(zip(names, translated, strict=False))
            for food in foods:
                original = food.get("description") or food.get("name", "")
                translated_name = name_map.get(original)
                if not translated_name:
                    continue
                if "description" in food:
                    food["description_original"] = original
                    food["description"] = translated_name
                if "name" in food:
                    food["name_original"] = original
                    food["name"] = translated_name
            return foods
        except Exception as exc:
            logger.warning(
                "Food-name translation failed (lang=%s): %s", target_lang, exc
            )
            return foods
