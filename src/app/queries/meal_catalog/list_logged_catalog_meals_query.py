"""Query for unique catalog meals this user has logged."""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class ListLoggedCatalogMealsQuery(Query):
    user_id: str
    limit: int = 20
