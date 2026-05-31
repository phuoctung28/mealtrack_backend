from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetCraveDeckQuery(Query):
    user_id: str
    meal_type: str
    deck_size: int = 15
    is_paid: bool = True
