"""Get drink catalog query."""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetDrinkCatalogQuery(Query):
    """Query to retrieve the static drink catalog."""

    language: str = "en"
