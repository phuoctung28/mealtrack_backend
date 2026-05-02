"""
Unit tests for GetMealsByDateQueryHandler.
"""

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.app.handlers.query_handlers.get_meals_by_date_query_handler import (
    GetMealsByDateQueryHandler,
)
from src.app.queries.meal import GetMealsByDateQuery
from src.domain.model import Meal, MealStatus, MealImage, Nutrition, FoodItem, Macros

_UOW_PATCH = (
    "src.app.handlers.query_handlers.get_meals_by_date_query_handler.AsyncUnitOfWork"
)


def _make_uow_mock():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.users.find_by_id = AsyncMock(return_value=None)
    return uow


def test_handler_initialization_with_repository():
    mock_repository = Mock()
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    assert handler.meal_repository == mock_repository


def test_handler_initialization_without_repository():
    handler = GetMealsByDateQueryHandler()
    assert handler.meal_repository is None


def test_set_dependencies():
    handler = GetMealsByDateQueryHandler()
    mock_repository = Mock()
    handler.set_dependencies(meal_repository=mock_repository)
    assert handler.meal_repository == mock_repository


@pytest.mark.asyncio
async def test_handle_with_no_meals_found():
    mock_repository = Mock()
    mock_repository.find_by_date.return_value = []
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    query = GetMealsByDateQuery(user_id="user123", meal_date=date(2024, 1, 15))

    with patch(_UOW_PATCH) as mock_cls:
        mock_cls.return_value = _make_uow_mock()
        result = await handler.handle(query)

    assert result == []
    mock_repository.find_by_date.assert_called_once()


@pytest.mark.asyncio
async def test_handle_with_single_meal_found():
    mock_repository = Mock()
    sample_meal = Meal(
        meal_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        status=MealStatus.READY,
        created_at=datetime.now(),
        image=MealImage(
            image_id=str(uuid.uuid4()),
            format="jpeg",
            size_bytes=10000,
            url="https://example.com/image.jpg",
        ),
        dish_name="Grilled Chicken",
        nutrition=Nutrition(
            macros=Macros(protein=30.0, carbs=20.0, fat=15.0),
            food_items=[],
            confidence_score=0.9,
        ),
        ready_at=datetime.now(),
    )
    mock_repository.find_by_date.return_value = [sample_meal]
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    query = GetMealsByDateQuery(user_id="user123", meal_date=date(2024, 1, 15))

    with patch(_UOW_PATCH) as mock_cls:
        mock_cls.return_value = _make_uow_mock()
        result = await handler.handle(query)

    assert len(result) == 1
    assert result[0].dish_name == "Grilled Chicken"


@pytest.mark.asyncio
async def test_handle_with_multiple_meals_found():
    mock_repository = Mock()
    meal1 = Meal(
        meal_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        status=MealStatus.READY,
        created_at=datetime.now(),
        image=MealImage(
            image_id=str(uuid.uuid4()),
            format="jpeg",
            size_bytes=10000,
            url="https://example.com/image1.jpg",
        ),
        dish_name="Breakfast",
        nutrition=Nutrition(
            macros=Macros(protein=20.0, carbs=30.0, fat=10.0),
            food_items=[],
            confidence_score=0.9,
        ),
        ready_at=datetime.now(),
    )
    meal2 = Meal(
        meal_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        status=MealStatus.READY,
        created_at=datetime.now(),
        image=MealImage(
            image_id=str(uuid.uuid4()),
            format="jpeg",
            size_bytes=10000,
            url="https://example.com/image2.jpg",
        ),
        dish_name="Lunch",
        nutrition=Nutrition(
            macros=Macros(protein=35.0, carbs=45.0, fat=20.0),
            food_items=[],
            confidence_score=0.9,
        ),
        ready_at=datetime.now(),
    )
    mock_repository.find_by_date.return_value = [meal1, meal2]
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    query = GetMealsByDateQuery(user_id="user123", meal_date=date(2024, 1, 15))

    with patch(_UOW_PATCH) as mock_cls:
        mock_cls.return_value = _make_uow_mock()
        result = await handler.handle(query)

    assert len(result) == 2
    assert result[0].dish_name == "Breakfast"
    assert result[1].dish_name == "Lunch"


@pytest.mark.asyncio
async def test_handle_filters_by_user_id():
    mock_repository = Mock()
    mock_repository.find_by_date.return_value = []
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    query = GetMealsByDateQuery(user_id="different_user", meal_date=date(2024, 1, 15))

    with patch(_UOW_PATCH) as mock_cls:
        mock_cls.return_value = _make_uow_mock()
        await handler.handle(query)

    mock_repository.find_by_date.assert_called_once()
    call_kwargs = mock_repository.find_by_date.call_args[1]
    assert call_kwargs["user_id"] == "different_user"


@pytest.mark.asyncio
async def test_handle_without_repository_raises_runtime_error():
    handler = GetMealsByDateQueryHandler()
    query = GetMealsByDateQuery(user_id="user123", meal_date=date(2024, 1, 15))

    with pytest.raises(RuntimeError) as exc_info:
        await handler.handle(query)

    assert "Meal repository not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_handle_with_different_dates():
    mock_repository = Mock()
    mock_repository.find_by_date.return_value = []
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    test_dates = [date(2024, 1, 1), date(2024, 12, 31), date(2024, 2, 29)]

    with patch(_UOW_PATCH) as mock_cls:
        mock_cls.return_value = _make_uow_mock()
        for test_date in test_dates:
            query = GetMealsByDateQuery(user_id="user123", meal_date=test_date)
            await handler.handle(query)

    mock_repository.find_by_date.assert_called()


@pytest.mark.asyncio
async def test_handle_preserves_meal_status():
    mock_repository = Mock()
    processing_meal = Meal(
        meal_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        status=MealStatus.PROCESSING,
        created_at=datetime.now(),
        image=MealImage(
            image_id=str(uuid.uuid4()),
            format="jpeg",
            size_bytes=10000,
            url="https://example.com/image1.jpg",
        ),
    )
    ready_meal = Meal(
        meal_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        status=MealStatus.READY,
        created_at=datetime.now(),
        image=MealImage(
            image_id=str(uuid.uuid4()),
            format="jpeg",
            size_bytes=10000,
            url="https://example.com/image2.jpg",
        ),
        dish_name="Ready Meal",
        nutrition=Nutrition(
            macros=Macros(protein=30.0, carbs=20.0, fat=15.0),
            food_items=[],
            confidence_score=0.9,
        ),
        ready_at=datetime.now(),
    )
    mock_repository.find_by_date.return_value = [processing_meal, ready_meal]
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    query = GetMealsByDateQuery(user_id="user123", meal_date=date(2024, 1, 15))

    with patch(_UOW_PATCH) as mock_cls:
        mock_cls.return_value = _make_uow_mock()
        result = await handler.handle(query)

    assert len(result) == 2
    assert result[0].status == MealStatus.PROCESSING
    assert result[1].status == MealStatus.READY


@pytest.mark.asyncio
async def test_handle_with_meals_containing_food_items():
    mock_repository = Mock()
    food_items = [
        FoodItem(
            id="food1",
            name="Chicken Breast",
            quantity=150.0,
            unit="g",
            macros=Macros(protein=46.2, carbs=0.0, fat=5.4),
            fdc_id=171077,
            is_custom=False,
        ),
        FoodItem(
            id="food2",
            name="Brown Rice",
            quantity=100.0,
            unit="g",
            macros=Macros(protein=2.6, carbs=22.0, fat=0.9),
            fdc_id=168880,
            is_custom=False,
        ),
    ]
    meal = Meal(
        meal_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        status=MealStatus.READY,
        created_at=datetime.now(),
        image=MealImage(
            image_id=str(uuid.uuid4()),
            format="jpeg",
            size_bytes=10000,
            url="https://example.com/image.jpg",
        ),
        dish_name="Chicken and Rice",
        nutrition=Nutrition(
            macros=Macros(protein=48.8, carbs=22.0, fat=6.3),
            food_items=food_items,
            confidence_score=0.9,
        ),
        ready_at=datetime.now(),
    )
    mock_repository.find_by_date.return_value = [meal]
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    query = GetMealsByDateQuery(user_id="user123", meal_date=date(2024, 1, 15))

    with patch(_UOW_PATCH) as mock_cls:
        mock_cls.return_value = _make_uow_mock()
        result = await handler.handle(query)

    assert len(result) == 1
    assert len(result[0].nutrition.food_items) == 2
    assert result[0].nutrition.food_items[0].name == "Chicken Breast"
    assert result[0].nutrition.food_items[1].name == "Brown Rice"


@pytest.mark.asyncio
async def test_handle_repository_exception_propagates():
    mock_repository = Mock()
    mock_repository.find_by_date.side_effect = Exception("Database connection error")
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    query = GetMealsByDateQuery(user_id="user123", meal_date=date(2024, 1, 15))

    with patch(_UOW_PATCH) as mock_cls:
        mock_cls.return_value = _make_uow_mock()
        with pytest.raises(Exception) as exc_info:
            await handler.handle(query)

    assert "Database connection error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_handle_with_today_date():
    mock_repository = Mock()
    mock_repository.find_by_date.return_value = []
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    query = GetMealsByDateQuery(user_id="user123", meal_date=date.today())

    with patch(_UOW_PATCH) as mock_cls:
        mock_cls.return_value = _make_uow_mock()
        result = await handler.handle(query)

    assert result == []
    mock_repository.find_by_date.assert_called_once()


@pytest.mark.asyncio
async def test_handle_called_multiple_times():
    mock_repository = Mock()
    mock_repository.find_by_date.return_value = []
    handler = GetMealsByDateQueryHandler(meal_repository=mock_repository)
    query1 = GetMealsByDateQuery(user_id="user1", meal_date=date(2024, 1, 15))
    query2 = GetMealsByDateQuery(user_id="user2", meal_date=date(2024, 1, 16))

    with patch(_UOW_PATCH) as mock_cls:
        mock_cls.return_value = _make_uow_mock()
        await handler.handle(query1)
        await handler.handle(query2)

    assert mock_repository.find_by_date.call_count == 2
