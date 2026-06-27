from unittest.mock import AsyncMock

import pytest

from src.infra.adapters.food_data_service import FoodDataService


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_get_branded_food_by_gtin_returns_exact_normalized_match():
    client = AsyncMock()
    client.get.return_value = _Response(
        {
            "foods": [
                {"fdcId": 1, "gtinUpc": "999999999999"},
                {"fdcId": 2, "gtinUpc": "036000291452"},
            ]
        }
    )
    service = FoodDataService(api_key="key", client=client)

    result = await service.get_branded_food_by_gtin(["00036000291452"])

    assert result is not None
    assert result["fdcId"] == 2


@pytest.mark.asyncio
async def test_get_branded_food_by_gtin_missing_key_returns_none():
    service = FoodDataService(api_key="", client=AsyncMock())

    assert await service.get_branded_food_by_gtin(["00036000291452"]) is None
