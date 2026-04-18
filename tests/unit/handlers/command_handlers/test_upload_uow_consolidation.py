"""Tests that upload_meal_image handler opens UnitOfWork at most twice on happy path."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.app.commands.meal.upload_meal_image_immediately_command import (
    UploadMealImageImmediatelyCommand,
)
from src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler import (
    UploadMealImageImmediatelyHandler,
)


def _make_meal_mock(meal_id=None):
    meal = MagicMock()
    meal.meal_id = meal_id or str(uuid4())
    meal.nutrition = MagicMock()
    meal.nutrition.food_items = [MagicMock()]
    meal.nutrition.calories = 400
    meal.status = MagicMock()
    return meal


_FAKE_IMAGE_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
_FAKE_USER_UUID = "00000000-0000-0000-0000-000000000001"


def _make_handler():
    handler = UploadMealImageImmediatelyHandler()
    handler.image_store = MagicMock()
    handler.image_store.save.return_value = f"mock://images/{_FAKE_IMAGE_UUID}"
    handler.vision_service = MagicMock()
    handler.vision_service.analyze.return_value = '{"dish_name": "Salad"}'
    handler.gpt_parser = MagicMock()
    handler.gpt_parser.parse_to_nutrition.return_value = MagicMock(
        food_items=[MagicMock()], calories=400
    )
    handler.gpt_parser.parse_dish_name.return_value = "Salad"
    handler.gpt_parser.parse_emoji.return_value = "🥗"
    handler.gpt_parser.extract_raw_json.return_value = "{}"
    handler.cache_service = None
    handler.meal_translation_service = None
    return handler


@pytest.mark.asyncio
async def test_happy_path_opens_uow_twice():
    """Happy path: UnitOfWork is opened exactly twice (merged 1+2 and merged 3+4)."""
    handler = _make_handler()
    cmd = UploadMealImageImmediatelyCommand(
        user_id=_FAKE_USER_UUID, file_contents=b"img", content_type="image/jpeg"
    )
    mock_meal = _make_meal_mock()

    with patch(
        "src.app.handlers.command_handlers"
        ".upload_meal_image_immediately_command_handler.UnitOfWork"
    ) as mock_cls:
        mock_uow = MagicMock()
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow.users.get_user_timezone.return_value = "UTC"
        mock_uow.meals.save.return_value = mock_meal
        mock_uow.meals.find_by_id.return_value = mock_meal
        mock_cls.return_value = mock_uow

        await handler.handle(cmd)

    assert mock_cls.call_count == 2, (
        f"Expected 2 UoW opens on happy path, got {mock_cls.call_count}"
    )


@pytest.mark.asyncio
async def test_timezone_and_initial_save_in_same_uow():
    """get_user_timezone and meals.save are called on the same UoW instance."""
    handler = _make_handler()
    cmd = UploadMealImageImmediatelyCommand(
        user_id=_FAKE_USER_UUID, file_contents=b"img", content_type="image/jpeg"
    )
    mock_meal = _make_meal_mock()
    uow_instances = []

    class TrackingUow:
        def __init__(self):
            self.users = MagicMock()
            self.users.get_user_timezone.return_value = "UTC"
            self.meals = MagicMock()
            self.meals.save.return_value = mock_meal
            self.meals.find_by_id.return_value = mock_meal
            uow_instances.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def commit(self):
            pass

    with patch(
        "src.app.handlers.command_handlers"
        ".upload_meal_image_immediately_command_handler.UnitOfWork",
        TrackingUow,
    ):
        await handler.handle(cmd)

    # First UoW instance must have both get_user_timezone and meals.save called
    first_uow = uow_instances[0]
    first_uow.users.get_user_timezone.assert_called_once()
    first_uow.meals.save.assert_called()
