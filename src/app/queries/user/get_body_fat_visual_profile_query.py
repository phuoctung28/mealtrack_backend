"""Query for a user's visual body-fat selection history."""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetBodyFatVisualProfileQuery(Query):
    """Get the latest visual body-fat selection and complete history."""

    user_id: str
