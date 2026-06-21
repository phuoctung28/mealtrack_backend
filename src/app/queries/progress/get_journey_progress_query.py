"""Query for the active journey progress snapshot."""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetJourneyProgressQuery(Query):
    user_id: str
    header_timezone: str | None = None
