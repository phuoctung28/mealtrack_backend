"""Internal suggestion translation outcome carrier."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.model.meal_suggestion import MealSuggestion
from src.domain.model.translation_result import TranslationOutcome


@dataclass(frozen=True)
class SuggestionTranslationResult:
    suggestion: MealSuggestion
    outcome: TranslationOutcome

    @property
    def persistable(self) -> bool:
        return self.outcome is TranslationOutcome.TRANSLATED
