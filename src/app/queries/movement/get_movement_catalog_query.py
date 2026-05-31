"""Query for backend-owned movement catalog."""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetMovementCatalogQuery(Query):
    pass
