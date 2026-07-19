"""Command for logging a durable recommendation slot as a normal meal."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class LogRecommendedMealCommand(Command):
    user_id: str
    plan_id: str
    slot_id: str
    request_id: str
