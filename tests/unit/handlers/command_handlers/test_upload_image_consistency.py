"""Tests for image-database consistency in upload handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock

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
    handler.image_store.save.side_effect = Exception("Cloudinary upload failed")

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
