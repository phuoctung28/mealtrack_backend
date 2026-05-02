"""
Port (interface) for DeepL translation service.
"""

from abc import ABC, abstractmethod
from typing import List


class DeepLTranslationPort(ABC):
    """Abstract interface for DeepL-backed text translation."""

    @abstractmethod
    async def translate_texts(self, texts: List[str], target_lang: str) -> List[str]:
        """
        Translate a list of strings to the target language in one batch.

        Args:
            texts: Strings to translate.
            target_lang: ISO 639-1 language code (e.g. 'vi', 'fr').

        Returns:
            Translated strings in the same order as the input.

        Raises:
            Exception: On any API-level failure (caller decides how to handle).
        """
