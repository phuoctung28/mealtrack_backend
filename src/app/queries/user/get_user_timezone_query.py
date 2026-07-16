"""Query to resolve a user's effective timezone."""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetUserTimezoneQuery(Query):
    """Resolve timezone using DB -> header -> UTC precedence."""

    user_id: str
    header_timezone: str | None = None
