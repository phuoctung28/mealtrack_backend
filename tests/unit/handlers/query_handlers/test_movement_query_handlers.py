import pytest

from src.app.handlers.query_handlers.get_movement_catalog_query_handler import (
    GetMovementCatalogQueryHandler,
)
from src.app.queries.movement import GetMovementCatalogQuery


@pytest.mark.asyncio
async def test_get_movement_catalog_query_returns_activities():
    handler = GetMovementCatalogQueryHandler()

    result = await handler.handle(GetMovementCatalogQuery())

    assert "activities" in result
    assert any(item["id"] == "badminton" for item in result["activities"])
