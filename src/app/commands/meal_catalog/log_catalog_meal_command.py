"""Command for logging a catalog meal as a normal meal."""

from dataclasses import dataclass
from datetime import date

from src.app.events.base import Command


@dataclass
class LogCatalogMealCommand(Command):
    user_id: str
    catalog_meal_id: str
    meal_date: date
    meal_type: str
    request_id: str
    timezone: str
    language: str | None = None
