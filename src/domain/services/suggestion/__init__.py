"""Suggestion domain services."""
# Re-export orchestration service for backward compatibility
from src.domain.services.meal_suggestion.suggestion_orchestration_service import (
    SuggestionOrchestrationService,
)
from .suggestion_service import SuggestionService

__all__ = ["SuggestionService", "SuggestionOrchestrationService"]
