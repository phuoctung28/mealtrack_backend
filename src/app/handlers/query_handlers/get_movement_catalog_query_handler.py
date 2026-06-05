"""Handler for movement catalog query."""

from typing import Any

from src.app.events.base import EventHandler, handles
from src.app.queries.movement import GetMovementCatalogQuery
from src.domain.services.movement_catalog_service import get_all_activities


@handles(GetMovementCatalogQuery)
class GetMovementCatalogQueryHandler(
    EventHandler[GetMovementCatalogQuery, dict[str, list[dict[str, Any]]]]
):
    async def handle(
        self, query: GetMovementCatalogQuery
    ) -> dict[str, list[dict[str, Any]]]:
        return {"activities": get_all_activities()}
