from dataclasses import dataclass

from src.app.events.base import DomainEvent


@dataclass
class MealSwipedEvent(DomainEvent):
    user_id: str
    catalog_meal_id: str
    direction: str
    meal_type: str | None = None
