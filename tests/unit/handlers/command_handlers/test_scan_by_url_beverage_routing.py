"""Unit tests for scan-by-url beverage routing."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.app.commands.meal.scan_by_url_command import ScanByUrlCommand
from src.app.handlers.command_handlers.scan_by_url_command_handler import (
    ScanByUrlCommandHandler,
)

_IMAGE_URL = "https://res.cloudinary.com/test/image/upload/v1/mealtrack/drink.jpg"
_USER_ID = "00000000-0000-0000-0000-000000000001"


def _make_uow() -> MagicMock:
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.users = MagicMock()
    uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    uow.meals = MagicMock()
    uow.meals.save = AsyncMock(side_effect=lambda meal: meal)
    uow.meals.find_by_id = AsyncMock()
    uow.hydration_entries = MagicMock()
    uow.hydration_entries.add = AsyncMock(side_effect=lambda entry: entry)
    uow.commit = AsyncMock()
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
async def test_scan_by_url_beverage_creates_hydration_entry_not_meal(monkeypatch):
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
                "foods": [],
                "beverage_metadata": {
                    "is_packaged_beverage": True,
                    "brand": "Coca-Cola",
                    "volume_ml": 330,
                    "kcal_per_100ml": 42.0,
                    "sugar_per_100ml": 10.6,
                    "label_source": "nutrition_panel",
                },
            }
        }
    )

    result = await handler.handle(
        ScanByUrlCommand(
            user_id=_USER_ID,
            image_url=_IMAGE_URL,
            public_id="mealtrack/drink",
        )
    )

    uow.hydration_entries.add.assert_awaited_once()
    added_entry = uow.hydration_entries.add.call_args[0][0]
    assert added_entry.source == "scan_beverage"
    assert added_entry.drink_name_snapshot == "Coca-Cola"
    assert added_entry.volume_ml == 330
    assert added_entry.image_url == _IMAGE_URL
    assert added_entry.legacy_meal_id is None
    assert added_entry.drink_id == "scanned"
    UUID(added_entry.id)

    uow.meals.save.assert_not_called()
    handler.gpt_parser.parse_is_food.assert_not_called()
    cache.after_hydration_write.assert_awaited_once()
    cache.after_meal_write.assert_not_called()

    assert result.meal_id == added_entry.id
    assert result.meal_type == "hydration"
    assert result.source == "scan_beverage"
    assert result.image.url == _IMAGE_URL


@pytest.mark.asyncio
async def test_scan_by_url_food_label_creates_ready_meal(monkeypatch):
    from src.domain.model.nutrition import FoodItem, Macros, Nutrition

    _install_fake_image_download(monkeypatch)
    uow = _make_uow()
    cache = MagicMock()
    cache.after_meal_write = AsyncMock()
    handler = ScanByUrlCommandHandler(
        uow=uow,
        event_bus=MagicMock(),
        vision_service=MagicMock(),
        gpt_parser=MagicMock(),
        cache_invalidation=cache,
    )
    handler.vision_service.analyze_food_label = AsyncMock(
        return_value={"is_food_label": True, "product_name": "Protein Bar"}
    )
    handler.gpt_parser.parse_food_label_to_nutrition.return_value = Nutrition(
        macros=Macros(protein=10, carbs=20, fat=5, fiber=4, sugar=8),
        food_items=[
            FoodItem(
                id="label-item",
                name="Protein Bar",
                quantity=55,
                unit="g",
                macros=Macros(protein=10, carbs=20, fat=5, fiber=4, sugar=8),
                is_custom=True,
            )
        ],
    )
    handler.gpt_parser.parse_food_label_metadata.return_value = {"is_food_label": True}
    handler.gpt_parser.parse_food_label_name.return_value = "Protein Bar"
    handler.gpt_parser.extract_raw_json.return_value = '{"product_name":"Protein Bar"}'
    handler.gpt_parser.parse_is_food = MagicMock()

    result = await handler.handle(
        ScanByUrlCommand(
            user_id=_USER_ID,
            image_url=_IMAGE_URL,
            public_id="mealtrack/00000000-0000-0000-0000-000000000002",
            scan_mode="food_label",
        )
    )

    handler.vision_service.analyze_food_label.assert_awaited_once_with(
        b"fake-image-bytes"
    )
    uow.meals.save.assert_awaited_once()
    handler.gpt_parser.parse_is_food.assert_not_called()
    cache.after_meal_write.assert_awaited_once()
    assert result.source == "food_label"
    assert result.dish_name == "Protein Bar"
    assert result.emoji is None
    assert result.nutrition.food_items[0].quantity == 55
