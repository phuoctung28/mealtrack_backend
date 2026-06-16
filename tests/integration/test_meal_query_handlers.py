"""
Integration tests for meal query handlers.
"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.exceptions import ResourceNotFoundException
from src.app.queries.meal import GetDailyMacrosQuery, GetMealByIdQuery
from src.domain.model import MealStatus
from src.infra.database.models.enums import MealStatusEnum
from src.infra.database.models.meal.meal import MealORM
from src.infra.database.models.meal.meal_image import MealImageORM


def create_test_meal_in_db(
    session,
    meal_id,
    dish_name,
    user_id="550e8400-e29b-41d4-a716-446655440001",
    created_at=None,
    calories=500,
    protein=30,
    carbs=50,
    fat=20,
):
    """Helper to create a test meal with proper structure."""
    import uuid

    from src.infra.database.models.nutrition.nutrition import NutritionORM

    # Create image
    image = MealImageORM(
        image_id=str(uuid.uuid4()),
        format="jpeg",
        size_bytes=100000,
        url=f"https://example.com/{meal_id}.jpg",
    )
    session.add(image)
    session.flush()

    # Create meal
    meal = MealORM(
        meal_id=meal_id,
        user_id=user_id,
        status=MealStatusEnum.READY,
        dish_name=dish_name,
        created_at=created_at or datetime.now(),
        image_id=image.image_id,
        ready_at=datetime.now(),
    )
    session.add(meal)
    session.flush()

    # Add nutrition
    nutrition = NutritionORM(
        meal_id=meal_id,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        confidence_score=0.95,
    )
    session.add(nutrition)

    return meal


@pytest.mark.integration
class TestGetMealByIdQueryHandler:
    """Test GetMealByIdQuery handler with database."""

    @pytest.mark.asyncio
    async def test_get_meal_by_id_success(self, event_bus, sample_meal_db):
        """Test successful meal retrieval by ID."""
        # Arrange
        query = GetMealByIdQuery(meal_id=sample_meal_db.meal_id)

        # Act
        meal = await event_bus.send(query)

        # Assert
        assert meal.meal_id == sample_meal_db.meal_id
        assert meal.status == MealStatus.READY
        assert meal.dish_name == sample_meal_db.dish_name
        assert meal.nutrition is not None
        assert meal.nutrition.calories == sample_meal_db.nutrition.calories

    @pytest.mark.asyncio
    async def test_get_meal_by_id_not_found(self, event_bus):
        """Test meal retrieval with non-existent ID."""
        # Arrange
        query = GetMealByIdQuery(meal_id="non-existent-meal")

        # Act & Assert
        with pytest.raises(ResourceNotFoundException):
            await event_bus.send(query)

    @pytest.mark.asyncio
    async def test_get_meal_by_id_falls_back_to_hydration_entry_alias(self, monkeypatch):
        """Scanned beverages return a meal-shaped response backed by hydration_entries."""
        from src.app.handlers.query_handlers import (
            get_meal_by_id_query_handler as module,
        )
        from src.domain.model.hydration import HydrationEntry

        entry_id = "11111111-1111-1111-1111-111111111111"
        user_id = "22222222-2222-2222-2222-222222222222"
        logged_at = datetime(2026, 6, 16, 12, 0)

        fake_uow = MagicMock()
        fake_uow.__aenter__ = AsyncMock(return_value=fake_uow)
        fake_uow.__aexit__ = AsyncMock(return_value=False)
        fake_uow.meals.find_by_id = AsyncMock(return_value=None)
        fake_uow.hydration_entries.find_by_id_or_legacy_meal_id = AsyncMock(
            return_value=HydrationEntry(
                id=entry_id,
                user_id=user_id,
                drink_id="scanned",
                drink_name_snapshot="Coca-Cola",
                emoji_snapshot="🥤",
                volume_ml=330,
                credited_ml=230,
                carbs_g=35.0,
                fat_g=0.0,
                sugar_g=35.0,
                logged_at=logged_at,
                source="scan_beverage",
                image_url="https://example.com/drink.jpg",
            )
        )
        monkeypatch.setattr(module, "AsyncUnitOfWork", lambda: fake_uow)

        meal = await module.GetMealByIdQueryHandler().handle(
            GetMealByIdQuery(meal_id=entry_id, user_id=user_id)
        )

        assert meal.meal_id == entry_id
        assert meal.meal_type == "hydration"
        assert meal.source == "scan_beverage"
        assert meal.dish_name == "Coca-Cola"
        assert meal.image.url == "https://example.com/drink.jpg"

    @pytest.mark.asyncio
    async def test_get_meal_by_id_with_food_items(
        self, event_bus, test_session, sample_meal_domain
    ):
        """Test meal retrieval includes food items."""
        # Arrange - Create meal with food items
        # First create the meal image
        import uuid

        from src.infra.database.models.nutrition.food_item import FoodItemORM
        from src.infra.database.models.nutrition.nutrition import NutritionORM

        meal_image = MealImageORM(
            image_id=str(uuid.uuid4()),
            url="https://example.com/image.jpg",
            format="jpeg",
            size_bytes=1024,
            width=800,
            height=600,
            created_at=datetime.now(),
        )
        test_session.add(meal_image)
        test_session.flush()

        # Create meal
        meal_id = str(uuid.uuid4())
        meal_model = MealORM(
            meal_id=meal_id,
            user_id="550e8400-e29b-41d4-a716-446655440001",
            status=MealStatusEnum.READY,
            dish_name="Test Meal with Items",
            created_at=datetime.now(),
            image_id=meal_image.image_id,
            ready_at=datetime.now(),
        )
        test_session.add(meal_model)
        test_session.flush()

        # Create nutrition
        nutrition = NutritionORM(
            meal_id=meal_id,
            calories=500,
            protein=30,
            carbs=50,
            fat=20,
            confidence_score=0.95,
        )
        test_session.add(nutrition)
        test_session.flush()

        # Add food items
        food_item1 = FoodItemORM(
            id="test-food-item-1",
            nutrition_id=nutrition.id,
            name="Rice",
            quantity=150,
            unit="g",
            calories=200,
            protein=5,
            carbs=40,
            fat=2,
            confidence=0.95,
        )
        food_item2 = FoodItemORM(
            id="test-food-item-2",
            nutrition_id=nutrition.id,
            name="Chicken",
            quantity=100,
            unit="g",
            calories=300,
            protein=25,
            carbs=10,
            fat=18,
            confidence=0.9,
        )
        test_session.add(food_item1)
        test_session.add(food_item2)
        test_session.commit()

        query = GetMealByIdQuery(meal_id=meal_id)

        # Act
        meal = await event_bus.send(query)

        # Assert
        assert meal.meal_id == meal_id
        assert meal.nutrition is not None
        assert len(meal.nutrition.food_items) == 2
        assert meal.nutrition.food_items[0].name == "Rice"
        assert meal.nutrition.food_items[1].name == "Chicken"


@pytest.mark.integration
class TestGetDailyMacrosQueryHandler:
    """Test GetDailyMacrosQuery handler with database."""

    @pytest.mark.asyncio
    async def test_get_daily_macros_success(self, event_bus, test_session):
        """Test successful daily macros calculation."""
        # Arrange - Create multiple meals for today
        import uuid

        today = date.today()

        # Create meal 0: 300 calories, 20 protein, 30 carbs, 10 fat
        create_test_meal_in_db(
            test_session,
            str(uuid.uuid4()),
            "Meal 0",
            created_at=datetime.combine(today, datetime.min.time()),
            calories=300,
            protein=20,
            carbs=30,
            fat=10,
        )

        # Create meal 1: 400 calories, 25 protein, 40 carbs, 15 fat
        create_test_meal_in_db(
            test_session,
            str(uuid.uuid4()),
            "Meal 1",
            created_at=datetime.combine(today, datetime.min.time())
            + timedelta(hours=4),
            calories=400,
            protein=25,
            carbs=40,
            fat=15,
        )

        # Create meal 2: 500 calories, 30 protein, 50 carbs, 20 fat
        create_test_meal_in_db(
            test_session,
            str(uuid.uuid4()),
            "Meal 2",
            created_at=datetime.combine(today, datetime.min.time())
            + timedelta(hours=8),
            calories=500,
            protein=30,
            carbs=50,
            fat=20,
        )

        test_session.commit()

        query = GetDailyMacrosQuery(
            user_id="550e8400-e29b-41d4-a716-446655440001", target_date=today
        )

        # Act
        result = await event_bus.send(query)

        # Assert
        assert result["date"] == today.isoformat()
        # Assert food_calories (gross), not total_calories (net = food - movement).
        # total_calories is net and depends on movement_entries rows; food_calories
        # is stable regardless of whether movement entries exist in the test DB.
        assert result["food_calories"] == 300 + 400 + 500  # 1200
        assert result["total_protein"] == 20 + 25 + 30  # 75
        assert result["total_carbs"] == 30 + 40 + 50  # 120
        assert result["total_fat"] == 10 + 15 + 20  # 45
        assert result["meal_count"] == 3

    @pytest.mark.asyncio
    async def test_get_daily_macros_empty(self, event_bus):
        """Test daily macros for date with no meals."""
        # Arrange
        future_date = date.today() + timedelta(days=365)
        query = GetDailyMacrosQuery(
            user_id="550e8400-e29b-41d4-a716-446655440001", target_date=future_date
        )

        # Act
        result = await event_bus.send(query)

        # Assert
        assert result["date"] == future_date.isoformat()
        assert result["total_calories"] == 0
        assert result["total_protein"] == 0
        assert result["total_carbs"] == 0
        assert result["total_fat"] == 0
        assert result["meal_count"] == 0
