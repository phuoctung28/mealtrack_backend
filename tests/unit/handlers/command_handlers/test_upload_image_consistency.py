"""Tests for image-database consistency in upload handler."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.app.commands.meal.upload_meal_image_immediately_command import (
    UploadMealImageImmediatelyCommand,
)
from src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler import (
    UploadMealImageImmediatelyHandler,
)


@pytest.mark.asyncio
async def test_upload_failure_does_not_create_db_record():
    """When Cloudinary upload fails, no meal record should be created in DB."""
    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users = MagicMock()
    mock_uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    mock_uow.meals = MagicMock()
    mock_uow.meals.save = AsyncMock()
    mock_uow.commit = AsyncMock()

    mock_event_bus = MagicMock()
    mock_event_bus.publish = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(
        uow=mock_uow,
        event_bus=mock_event_bus,
    )

    # Cloudinary upload fails
    handler.image_store = MagicMock()
    handler.image_store.save_async = AsyncMock(side_effect=Exception("Cloudinary upload failed"))

    handler.vision_service = MagicMock()
    handler.gpt_parser = MagicMock()

    command = UploadMealImageImmediatelyCommand(
        user_id="00000000-0000-0000-0000-000000000001",
        file_contents=b"fake-image-bytes",
        content_type="image/jpeg",
    )

    with pytest.raises(Exception, match="Cloudinary upload failed"):
        await handler.handle(command)

    # Key assertion: meals.save should NOT have been called
    mock_uow.meals.save.assert_not_called()
    mock_uow.commit.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_cloudinary_url_does_not_create_db_record_or_log_url(caplog):
    """When Cloudinary returns invalid URL, no meal record should be created."""
    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users = MagicMock()
    mock_uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    mock_uow.meals = MagicMock()
    mock_uow.meals.save = AsyncMock()
    mock_uow.commit = AsyncMock()

    mock_event_bus = MagicMock()
    mock_event_bus.publish = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(
        uow=mock_uow,
        event_bus=mock_event_bus,
    )

    # Cloudinary returns invalid URL (just the image_id, not a URL)
    handler.image_store = MagicMock()
    handler.image_store.save_async = AsyncMock(return_value="just-an-id-not-a-url")

    handler.vision_service = MagicMock()
    handler.gpt_parser = MagicMock()

    command = UploadMealImageImmediatelyCommand(
        user_id="00000000-0000-0000-0000-000000000001",
        file_contents=b"fake-image-bytes",
        content_type="image/jpeg",
    )

    with caplog.at_level("ERROR"):
        with pytest.raises(RuntimeError, match="Cloudinary upload failed"):
            await handler.handle(command)

    mock_uow.meals.save.assert_not_called()
    mock_uow.commit.assert_not_called()
    assert "just-an-id-not-a-url" not in caplog.text


@pytest.mark.asyncio
async def test_successful_upload_creates_meal_with_verified_url():
    """When upload succeeds with valid URL, meal is created with that URL."""
    saved_meals = []

    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users = MagicMock()
    mock_uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    mock_uow.meals = MagicMock()

    async def capture_save(meal):
        saved_meals.append(meal)
        return meal

    mock_uow.meals.save = AsyncMock(side_effect=capture_save)
    mock_uow.meals.find_by_id = AsyncMock(side_effect=lambda mid, **kw: saved_meals[-1])
    mock_uow.commit = AsyncMock()

    mock_event_bus = MagicMock()
    mock_event_bus.publish = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(
        uow=mock_uow,
        event_bus=mock_event_bus,
    )

    # Cloudinary returns valid URL
    handler.image_store = MagicMock()
    handler.image_store.save_async = AsyncMock(return_value=(
        "https://res.cloudinary.com/test/image/upload/v123/mealtrack/abc123.jpg"
    ))

    # Vision service returns valid analysis
    handler.vision_service = MagicMock()
    handler.vision_service.analyze = AsyncMock(return_value={"dish_name": "Test Dish"})

    # Parser returns valid nutrition
    handler.gpt_parser = MagicMock()
    nutrition = SimpleNamespace(
        food_items=[SimpleNamespace(name="item1")],
        calories=400,
    )
    handler.gpt_parser.parse_to_nutrition.return_value = nutrition
    handler.gpt_parser.parse_dish_name.return_value = "Test Dish"
    handler.gpt_parser.parse_emoji.return_value = None
    handler.gpt_parser.extract_raw_json.return_value = "{}"

    command = UploadMealImageImmediatelyCommand(
        user_id="00000000-0000-0000-0000-000000000001",
        file_contents=b"fake-image-bytes",
        content_type="image/jpeg",
    )

    await handler.handle(command)

    # Verify meal was saved with the Cloudinary URL
    assert len(saved_meals) > 0
    final_meal = saved_meals[-1]
    assert (
        final_meal.image.url
        == "https://res.cloudinary.com/test/image/upload/v123/mealtrack/abc123.jpg"
    )
    assert final_meal.status.value == "READY"
