"""Port for provider-backed text translation."""

from abc import ABC, abstractmethod


class TextTranslationPort(ABC):
    """Abstract interface for text translation."""

    @abstractmethod
    async def translate_texts(self, texts: list[str], target_lang: str) -> list[str]:
        """Translate canonical English strings to the target language."""

    @abstractmethod
    async def translate_to_english(
        self, texts: list[str], source_lang: str
    ) -> list[str]:
        """Translate strings from the source language to English."""
