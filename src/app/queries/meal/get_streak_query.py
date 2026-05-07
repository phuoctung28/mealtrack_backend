"""
Get streak query.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetStreakQuery(Query):
    """Query to get user's current and best logging streak."""

    user_id: str
    header_timezone: Optional[str] = None
