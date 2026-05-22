"""Get drink catalog query."""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetDrinkCatalogQuery(Query):
    """Query to retrieve the static drink catalog. No parameters — returns catalog for all users."""

    pass  # No parameters — returns static catalog for all users
