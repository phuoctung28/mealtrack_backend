from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetCraveRecipeQuery(Query):
    catalog_meal_id: str
