"""Unit tests for scan-by-url beverage meal behavior."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.app.commands.meal.scan_by_url_command import ScanByUrlCommand
from src.app.handlers.command_handlers.scan_by_url_command_handler import (
    ScanByUrlCommandHandler,
)
from src.domain.parsers.vision_response_parser import VisionResponseParser

_IMAGE_URL = "https://res.cloudinary.com/test/image/upload/v1/mealtrack/drink.jpg"
_PUBLIC_ID = "mealtrack/1325c7ca-e012-4df3-b0b4-55bfaeb55eb0"
_USER_ID = "00000000-0000-0000-0000-000000000001"


def _make_uow() -> MagicMock:
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.users = MagicMock()
    uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    uow.meals = MagicMock()
    saved_meals = []

    async def capture_meal(meal):
        saved_meals.append(meal)
        return meal

    uow.meals.save = AsyncMock(side_effect=capture_meal)
    uow.meals.find_by_id = AsyncMock(side_effect=lambda mid, **kw: saved_meals[-1])
    uow.hydration_entries = MagicMock()
    uow.hydration_entries.add = AsyncMock(side_effect=lambda entry: entry)
    uow.commit = AsyncMock()
    uow._saved_meals = saved_meals
    return uow


def _install_fake_image_download(monkeypatch) -> None:
    from src.app.handlers.command_handlers import scan_by_url_command_handler as module

    class FakeResponse:
        content = b"fake-image-bytes"

        def raise_for_status(self):
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(module.httpx, "AsyncClient", lambda timeout: FakeClient())
    monkeypatch.setattr(module, "compress_image", lambda raw_bytes: raw_bytes)


@pytest.mark.asyncio
async def test_scan_by_url_packaged_beverage_creates_standard_meal(monkeypatch):
    _install_fake_image_download(monkeypatch)
    uow = _make_uow()
    cache = MagicMock()
    cache.after_hydration_write = AsyncMock()
    cache.after_meal_write = AsyncMock()

    handler = ScanByUrlCommandHandler(
        uow=uow,
        event_bus=MagicMock(),
        vision_service=MagicMock(),
        gpt_parser=MagicMock(),
        cache_invalidation=cache,
    )
    handler.vision_service.analyze = AsyncMock(
        return_value={
            "structured_data": {
                "is_food": True,
                "dish_name": "Coca-Cola",
                "foods": [
                    {
                        "name": "Coca-Cola",
                        "quantity_g": 330,
                        "macros": {
                            "protein_g": 0,
                            "carbs_g": 35,
                            "fat_g": 0,
                            "fiber_g": 0,
                            "sugar_g": 35,
                        },
                    }
                ],
                "beverage_metadata": None,
            }
        }
    )
    handler.gpt_parser = VisionResponseParser()

    result = await handler.handle(
        ScanByUrlCommand(
            user_id=_USER_ID,
            image_url=_IMAGE_URL,
            public_id=_PUBLIC_ID,
        )
    )

    uow.hydration_entries.add.assert_not_called()
    uow.meals.save.assert_awaited_once()
    cache.after_meal_write.assert_awaited_once()
    cache.after_hydration_write.assert_not_called()

    assert result.meal_id == uow._saved_meals[0].meal_id
    assert result.source == "scanner"
    assert result.image.url == _IMAGE_URL
