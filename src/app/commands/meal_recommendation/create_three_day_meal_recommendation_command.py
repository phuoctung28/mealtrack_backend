"""Command for durable catalog-backed three-day recommendation creation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.app.events.base import Command


@dataclass
class CreateThreeDayMealRecommendationCommand(Command):
    """Create or replay a durable owner-scoped three-day recommendation plan."""

    user_id: str
    idempotency_key: str
    start_date: date
    timezone: str
    daily_calories: int = 2000
    operation: str = "three_day"
