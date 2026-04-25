"""
DeepL translation adapter.

Wraps the official deepl Python SDK and maps ISO 639-1 language codes
to the codes expected by the DeepL API v2.
"""

import asyncio
import logging
from typing import List

import deepl

from src.domain.ports.deepl_translation_port import DeepLTranslationPort

logger = logging.getLogger(__name__)

# Map from ISO 639-1 used in the app to DeepL target-language codes.
_LANG_MAP: dict = {
    "en": "EN-US",
    "vi": "VI",
    "es": "ES",
    "fr": "FR",
    "de": "DE",
    "ja": "JA",
    "zh": "ZH",
    "ko": "KO",
    "pt": "PT-BR",
    "ru": "RU",
    "it": "IT",
    "nl": "NL",
    "pl": "PL",
    "tr": "TR",
    "uk": "UK",
    "id": "ID",
}


class DeepLTranslationAdapter(DeepLTranslationPort):
    """Translates text via the DeepL API."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("DEEPL_API_KEY is required")
        self._translator = deepl.Translator(auth_key=api_key)

    async def translate_texts(self, texts: List[str], target_lang: str) -> List[str]:
        """
        Translate a batch of strings with a single DeepL API call.

        Uses asyncio.to_thread so the blocking SDK call does not stall the
        event loop.
        """
        if not texts:
            return []

        deepl_lang = _LANG_MAP.get(target_lang.lower(), target_lang.upper())

        try:
            results = await asyncio.to_thread(
                self._translator.translate_text,
                texts,
                target_lang=deepl_lang,
            )
            # SDK returns a single TextResult when given a single string,
            # or a list when given a list.
            if isinstance(results, list):
                return [r.text for r in results]
            return [results.text]
        except deepl.DeepLException as exc:
            logger.error("DeepL API error (lang=%s): %s", deepl_lang, exc)
            raise
