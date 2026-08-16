"""Provider-neutral translation outcomes."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class TranslationOutcome(StrEnum):
    """Outcome categories used for presentation and cache admission."""

    TRANSLATED = "translated"
    PARTIAL = "partial"
    PASSTHROUGH = "passthrough"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class TranslationResult:
    """Immutable ordered translation result with explicit cacheability."""

    texts: tuple[str, ...]
    outcome: TranslationOutcome
    source_language: str
    target_language: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "texts", tuple(str(text) for text in self.texts))

    @property
    def items(self) -> tuple[str, ...]:
        return self.texts

    @property
    def translations(self) -> tuple[str, ...]:
        return self.texts

    @property
    def cacheable(self) -> bool:
        return self.outcome is TranslationOutcome.TRANSLATED

    @property
    def is_cacheable(self) -> bool:
        return self.cacheable

    def to_list(self) -> list[str]:
        return list(self.texts)

    @classmethod
    def passthrough(
        cls, texts: Iterable[str], *, source_language: str, target_language: str
    ) -> TranslationResult:
        return cls(
            tuple(texts),
            TranslationOutcome.PASSTHROUGH,
            source_language,
            target_language,
        )

    @classmethod
    def unavailable(
        cls, texts: Iterable[str], *, source_language: str, target_language: str
    ) -> TranslationResult:
        return cls(
            tuple(texts),
            TranslationOutcome.UNAVAILABLE,
            source_language,
            target_language,
        )
