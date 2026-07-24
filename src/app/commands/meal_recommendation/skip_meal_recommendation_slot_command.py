"""Command for skipping a durable recommendation slot."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class SkipMealRecommendationSlotCommand(Command):
    user_id: str
    plan_id: str
    slot_id: str
    request_id: str
