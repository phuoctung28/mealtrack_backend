"""Command for logging another meal from an already logged catalog slot."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class RelogRecommendedMealCommand(Command):
    user_id: str
    plan_id: str
    slot_id: str
    request_id: str
    language: str = "en"
