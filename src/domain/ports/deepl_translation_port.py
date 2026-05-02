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
        Translate a list of strings from English to the target language in one batch.

        Implementations must call DeepL with a fixed English source (no
        auto-detect). Non-English inputs are invalid for this port.

        Args:
            texts: English strings to translate.
            target_lang: ISO 639-1 target code (e.g. 'vi', 'fr'). Use 'en' only
                when the desired output is unchanged English (implementations
                may skip the API).

        Returns:
            Translated strings in the same order as the input.

        Raises:
            Exception: On any API-level failure (caller decides how to handle).
        """
