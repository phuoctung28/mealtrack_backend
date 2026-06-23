"""Unit tests for beverage scan routing in UploadMealImageImmediatelyHandler.

Verifies that packaged beverage images are routed to hydration_entries
instead of the standard meal path, and that food scans are unchanged.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.app.commands.meal.upload_meal_image_immediately_command import (
    UploadMealImageImmediatelyCommand,
)
from src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler import (
    UploadMealImageImmediatelyHandler,
)

_CLOUDINARY_URL = "https://res.cloudinary.com/test/image/upload/v1/mealtrack/drink.jpg"
_USER_ID = "00000000-0000-0000-0000-000000000001"


def _make_uow(*, save_return=None):
    """Build a minimal async-context-manager UoW mock."""
    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users = MagicMock()
    mock_uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    mock_uow.meals = MagicMock()
    mock_uow.meals.find_by_id = AsyncMock(side_effect=lambda mid, **kw: save_return)

    saved_meals = []

    async def capture_meal(meal):
        saved_meals.append(meal)
        return meal

    mock_uow.meals.save = AsyncMock(side_effect=capture_meal)
    mock_uow.hydration_entries = MagicMock()
    mock_uow.hydration_entries.add = AsyncMock(side_effect=lambda e: e)
    mock_uow.commit = AsyncMock()
    mock_uow._saved_meals = saved_meals
    return mock_uow


def _make_command(user_id: str = _USER_ID) -> UploadMealImageImmediatelyCommand:
    return UploadMealImageImmediatelyCommand(
        user_id=user_id,
        file_contents=b"fake-image-bytes",
        content_type="image/jpeg",
    )


@pytest.mark.asyncio
async def test_beverage_scan_creates_hydration_entry_not_meal():
    """When vision returns is_packaged_beverage=True, write hydration entry, not a standard meal."""
    mock_uow = _make_uow()
    cache = MagicMock()
    cache.after_hydration_write = AsyncMock()
    cache.after_meal_write = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(
        uow=mock_uow,
        event_bus=MagicMock(),
        cache_invalidation=cache,
    )
    handler.image_store = MagicMock()
    handler.image_store.save_async = AsyncMock(return_value=_CLOUDINARY_URL)
    handler.gpt_parser = MagicMock()

    bev_analysis = {
        "structured_data": {
            "is_food": True,
            "dish_name": "Coca-Cola",
            "foods": [],
            "confidence": 0.9,
            "beverage_metadata": {
                "is_packaged_beverage": True,
                "brand": "Coca-Cola",
                "product_name": "Coca-Cola Original",
                "volume_ml": 330,
                "kcal_per_100ml": 42.0,
                "sugar_per_100ml": 10.6,
                "label_source": "nutrition_panel",
            },
        }
    }
    handler.vision_service = MagicMock()
    handler.vision_service.analyze = AsyncMock(return_value=bev_analysis)

    result = await handler.handle(_make_command())

    # Hydration entry must be created
    mock_uow.hydration_entries.add.assert_called_once()
    added_entry = mock_uow.hydration_entries.add.call_args[0][0]
    assert added_entry.source == "scan_beverage"
    assert added_entry.drink_name_snapshot == "Coca-Cola"
    assert added_entry.volume_ml == 330
    assert added_entry.image_url == _CLOUDINARY_URL

    # Beverage scan should be hydration-only: no legacy meal row/link.
    assert len(mock_uow._saved_meals) == 0
    assert added_entry.legacy_meal_id is None
    assert added_entry.drink_id == "scanned"
    UUID(added_entry.id)

    # Cache invalidation: after_hydration_write called, NOT after_meal_write
    cache.after_hydration_write.assert_called_once()
    cache.after_meal_write.assert_not_called()

    # Return value keeps the meal-shaped API response but points at hydration entry.
    assert result.meal_id == added_entry.id
    assert result.meal_type == "hydration"
    assert result.source == "scan_beverage"
    assert result.image.url == _CLOUDINARY_URL


@pytest.mark.asyncio
async def test_beverage_scan_emits_warning_for_estimate_label_source(caplog):
    """When label_source='estimate', a WARNING is logged with brand and kcal."""
    mock_uow = _make_uow()
    cache = MagicMock()
    cache.after_hydration_write = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(
        uow=mock_uow,
        event_bus=MagicMock(),
        cache_invalidation=cache,
    )
    handler.image_store = MagicMock()
    handler.image_store.save_async = AsyncMock(return_value=_CLOUDINARY_URL)
    handler.gpt_parser = MagicMock()

    bev_analysis = {
        "structured_data": {
            "is_food": True,
            "beverage_metadata": {
                "is_packaged_beverage": True,
                "brand": "Unknown Brand",
                "volume_ml": 500,
                "kcal_per_100ml": 30.0,
                "sugar_per_100ml": 6.0,
                "label_source": "estimate",
            },
        }
    }
    handler.vision_service = MagicMock()
    handler.vision_service.analyze = AsyncMock(return_value=bev_analysis)

    import logging

    with caplog.at_level(logging.WARNING):
        await handler.handle(_make_command())

    assert "BEVERAGE-KCAL-ESTIMATE" in caplog.text
    assert "Unknown Brand" in caplog.text


@pytest.mark.asyncio
async def test_beverage_scan_hydration_weight_conservative_for_estimate():
    """Beverages with label_source='estimate' get hydration_weight=0.70."""
    mock_uow = _make_uow()
    cache = MagicMock()
    cache.after_hydration_write = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(
        uow=mock_uow,
        event_bus=MagicMock(),
        cache_invalidation=cache,
    )
    handler.image_store = MagicMock()
    handler.image_store.save_async = AsyncMock(return_value=_CLOUDINARY_URL)
    handler.gpt_parser = MagicMock()

    bev_analysis = {
        "structured_data": {
            "is_food": True,
            "beverage_metadata": {
                "is_packaged_beverage": True,
                "brand": "Mystery Drink",
                "volume_ml": 1000,
                "kcal_per_100ml": 20.0,
                "sugar_per_100ml": 4.0,
                "label_source": "estimate",
            },
        }
    }
    handler.vision_service = MagicMock()
    handler.vision_service.analyze = AsyncMock(return_value=bev_analysis)

    await handler.handle(_make_command())

    added_entry = mock_uow.hydration_entries.add.call_args[0][0]
    # volume=1000, hydration_weight=0.70 → credited_ml=700
    assert added_entry.credited_ml == 700


@pytest.mark.asyncio
async def test_food_scan_unchanged_path():
    """Non-beverage food scans follow the standard meal creation path."""
    mock_uow = _make_uow()
    mock_uow.meals.find_by_id = AsyncMock(
        side_effect=lambda mid, **kw: mock_uow._saved_meals[-1]
    )
    cache = MagicMock()
    cache.after_meal_write = AsyncMock()
    cache.after_hydration_write = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(
        uow=mock_uow,
        event_bus=MagicMock(),
        cache_invalidation=cache,
    )
    handler.image_store = MagicMock()
    handler.image_store.save_async = AsyncMock(return_value=_CLOUDINARY_URL)

    # Standard food analysis — no beverage_metadata
    food_analysis = {
        "structured_data": {
            "is_food": True,
            "dish_name": "Pho",
            "foods": [{"name": "Pho", "quantity_g": 500}],
            "confidence": 0.95,
        }
    }
    handler.vision_service = MagicMock()
    handler.vision_service.analyze = AsyncMock(return_value=food_analysis)

    nutrition = SimpleNamespace(
        food_items=[SimpleNamespace(name="Pho")],
        calories=450,
        macros=SimpleNamespace(protein=20, carbs=60, fat=10, fiber=2, sugar=5),
    )
    handler.gpt_parser = MagicMock()
    handler.gpt_parser.parse_is_food.return_value = True
    handler.gpt_parser.parse_to_nutrition.return_value = nutrition
    handler.gpt_parser.parse_dish_name.return_value = "Pho"
    handler.gpt_parser.parse_emoji.return_value = "🍜"
    handler.gpt_parser.extract_raw_json.return_value = "{}"

    await handler.handle(_make_command())

    # Standard meal path: no hydration entry
    mock_uow.hydration_entries.add.assert_not_called()

    # Meal saved with source="scanner"
    assert len(mock_uow._saved_meals) >= 1
    assert mock_uow._saved_meals[0].source == "scanner"

    # after_meal_write called, NOT after_hydration_write
    cache.after_meal_write.assert_called_once()
    cache.after_hydration_write.assert_not_called()


@pytest.mark.asyncio
async def test_food_scan_with_beverage_metadata_false_follows_food_path():
    """is_packaged_beverage=False on beverage_metadata still routes to food path."""
    mock_uow = _make_uow()
    mock_uow.meals.find_by_id = AsyncMock(
        side_effect=lambda mid, **kw: mock_uow._saved_meals[-1]
    )
    cache = MagicMock()
    cache.after_meal_write = AsyncMock()
    cache.after_hydration_write = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(
        uow=mock_uow,
        event_bus=MagicMock(),
        cache_invalidation=cache,
    )
    handler.image_store = MagicMock()
    handler.image_store.save_async = AsyncMock(return_value=_CLOUDINARY_URL)

    food_analysis = {
        "structured_data": {
            "is_food": True,
            "dish_name": "Smoothie bowl",
            "foods": [{"name": "Smoothie bowl", "quantity_g": 300}],
            "confidence": 0.85,
            "beverage_metadata": {
                "is_packaged_beverage": False,  # not packaged
            },
        }
    }
    handler.vision_service = MagicMock()
    handler.vision_service.analyze = AsyncMock(return_value=food_analysis)

    nutrition = SimpleNamespace(
        food_items=[SimpleNamespace(name="Smoothie bowl")],
        calories=300,
        macros=SimpleNamespace(protein=5, carbs=50, fat=8, fiber=3, sugar=20),
    )
    handler.gpt_parser = MagicMock()
    handler.gpt_parser.parse_is_food.return_value = True
    handler.gpt_parser.parse_to_nutrition.return_value = nutrition
    handler.gpt_parser.parse_dish_name.return_value = "Smoothie bowl"
    handler.gpt_parser.parse_emoji.return_value = "🥣"
    handler.gpt_parser.extract_raw_json.return_value = "{}"

    await handler.handle(_make_command())

    mock_uow.hydration_entries.add.assert_not_called()
    cache.after_meal_write.assert_called_once()
    cache.after_hydration_write.assert_not_called()
