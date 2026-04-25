"""Query to get all saved suggestions for a user."""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetSavedSuggestionsQuery(Query):
    """Retrieve all saved suggestions for a user, newest first."""

    user_id: str
