"""
Suggestion command/query handlers.
Session-based meal suggestion handlers using SuggestionOrchestrationService.
"""

from .accept_suggestion_handler import AcceptSuggestionHandler
from .discard_session_handler import DiscardSessionHandler
from .generate_meal_suggestions_handler import GenerateMealSuggestionsHandler
from .get_session_suggestions_handler import GetSessionSuggestionsHandler
from .regenerate_suggestions_handler import RegenerateSuggestionsHandler
from .reject_suggestion_handler import RejectSuggestionHandler

__all__ = [
    "GenerateMealSuggestionsHandler",
    "RegenerateSuggestionsHandler",
    "GetSessionSuggestionsHandler",
    "AcceptSuggestionHandler",
    "RejectSuggestionHandler",
    "DiscardSessionHandler",
]
