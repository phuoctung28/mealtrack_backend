"""Query to get user's weight entries."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GetWeightEntriesQuery:
    """Get weight entries for a user."""

    user_id: str
    limit: int = 100
    offset: int = 0
