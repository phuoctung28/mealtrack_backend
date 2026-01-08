"""Suggestion domain services."""
from .suggestion_service import SuggestionService

# Re-export orchestration service for backward compatibility
from src.domain.services.meal_suggestion.suggestion_orchestration_service import (
    SuggestionOrchestrationService,
)

__all__ = ["SuggestionService", "SuggestionOrchestrationService"]
