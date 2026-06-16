"""Tests for non-food guard behavior across image command handlers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.app.commands.meal.scan_by_url_command import ScanByUrlCommand
from src.app.handlers.command_handlers.scan_by_url_command_handler import (
    ScanByUrlCommandHandler,
)


def _uow_with_timezone() -> MagicMock:
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.users = MagicMock()
    uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    uow.meals = MagicMock()
    uow.meals.save = AsyncMock()
    uow.meals.find_by_id = AsyncMock()
    uow.commit = AsyncMock()
    return uow


@pytest.mark.asyncio
async def test_scan_by_url_rejects_non_food_before_meal_creation(monkeypatch):
    """scan-by-url should stop before nutrition parsing or persistence."""
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

    uow = _uow_with_timezone()
    handler = ScanByUrlCommandHandler(uow=uow, event_bus=MagicMock())
    handler.vision_service = MagicMock()
    handler.vision_service.analyze = AsyncMock(
        return_value={"structured_data": {"is_food": False, "foods": []}}
    )
    handler.gpt_parser = MagicMock()
    handler.gpt_parser.parse_is_food.return_value = False

    command = ScanByUrlCommand(
        user_id="00000000-0000-0000-0000-000000000001",
        image_url="https://res.cloudinary.com/test/image/upload/v123/mealtrack/abc.jpg",
        public_id="mealtrack/abc",
    )

    with pytest.raises(ValueError, match="Image does not appear to contain food"):
        await handler.handle(command)

    handler.gpt_parser.parse_to_nutrition.assert_not_called()
    uow.meals.save.assert_not_called()
