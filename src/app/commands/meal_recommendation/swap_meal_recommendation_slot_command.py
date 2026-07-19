"""Command for swapping one durable recommendation slot."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class SwapMealRecommendationSlotCommand(Command):
    user_id: str
    plan_id: str
    slot_id: str
    request_id: str
    expected_selection_version: int
    alternative_catalog_meal_id: str | None = None
    reason: str = "user_requested"
