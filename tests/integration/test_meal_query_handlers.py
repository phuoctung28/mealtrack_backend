"""
Integration tests for meal query handlers.
"""
from datetime import datetime, date, timedelta

import pytest

from src.api.exceptions import ResourceNotFoundException
from src.app.queries.meal import (
    GetMealByIdQuery,
    GetMealsByDateQuery,
    GetDailyMacrosQuery
)
from src.domain.model.meal import MealStatus
from src.infra.database.models.enums import MealStatusEnum
from src.infra.database.models.meal.meal import Meal as MealModel
from src.infra.database.models.meal.meal_image import MealImage as MealImageModel


def create_test_meal_in_db(session, meal_id, dish_name, user_id="550e8400-e29b-41d4-a716-446655440001", created_at=None, 
                          calories=500, protein=30, carbs=50, fat=20):
    """Helper to create a test meal with proper structure."""
    import uuid
    from src.infra.database.models.nutrition.nutrition import Nutrition as NutritionModel
    
    # Create image
    image = MealImageModel(
        image_id=str(uuid.uuid4()),
        format="jpeg",
        size_bytes=100000,
        url=f"https://example.com/{meal_id}.jpg"
    )
    session.add(image)
    session.flush()
    
    # Create meal
    meal = MealModel(
        meal_id=meal_id,
        user_id=user_id,
        status=MealStatusEnum.READY,
        dish_name=dish_name,
        created_at=created_at or datetime.now(),
        image_id=image.image_id,
        ready_at=datetime.now()
    )
    session.add(meal)
    session.flush()
    
    # Add nutrition
    nutrition = NutritionModel(
        meal_id=meal_id,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        confidence_score=0.95
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
    async def test_get_meal_by_id_with_food_items(
        self, event_bus, test_session, sample_meal_domain
    ):
        """Test meal retrieval includes food items."""
        # Arrange - Create meal with food items
        from src.infra.database.models.nutrition.food_item import FoodItem
        from src.infra.database.models.nutrition.nutrition import Nutrition
        
        # First create the meal image
        import uuid
        meal_image = MealImageModel(
            image_id=str(uuid.uuid4()),
            url="https://example.com/image.jpg",
            format="jpeg",
            size_bytes=1024,
            width=800,
            height=600,
            created_at=datetime.now()
        )
        test_session.add(meal_image)
        test_session.flush()
        
        # Create meal
        meal_id = str(uuid.uuid4())
        meal_model = MealModel(
            meal_id=meal_id,
            user_id="550e8400-e29b-41d4-a716-446655440001",
            status=MealStatusEnum.READY,
            dish_name="Test Meal with Items",
            created_at=datetime.now(),
            image_id=meal_image.image_id,
            ready_at=datetime.now()
        )
        test_session.add(meal_model)
        test_session.flush()
        
        # Create nutrition
        nutrition = Nutrition(
            meal_id=meal_id,
            calories=500,
            protein=30,
            carbs=50,
            fat=20,
            confidence_score=0.95
        )
        test_session.add(nutrition)
        test_session.flush()
        
        # Add food items
        food_item1 = FoodItem(
            id="test-food-item-1",
            nutrition_id=nutrition.id,
            name="Rice",
            quantity=150,
            unit="g",
            calories=200,
            protein=5,
            carbs=40,
            fat=2,
            confidence=0.95
        )
        food_item2 = FoodItem(
            id="test-food-item-2",
            nutrition_id=nutrition.id,
            name="Chicken",
            quantity=100,
            unit="g",
            calories=300,
            protein=25,
            carbs=10,
            fat=18,
            confidence=0.9
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
class TestGetMealsByDateQueryHandler:
    """Test GetMealsByDateQuery handler with database."""
    
    @pytest.mark.asyncio
    async def test_get_meals_by_date_success(self, event_bus, test_session):
        """Test successful meals retrieval by date."""
        # Arrange - Create meals for today
        import uuid
        today = date.today()
        
        meal1_id = str(uuid.uuid4())
        meal2_id = str(uuid.uuid4())
        
        # Create meals using helper function
        create_test_meal_in_db(
            test_session,
            meal1_id,
            "Breakfast",
            created_at=datetime.combine(today, datetime.min.time()),
            calories=300,
            protein=20,
            carbs=30,
            fat=10,
        )
        
        create_test_meal_in_db(
            test_session,
            meal2_id,
            "Lunch",
            created_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=4),
            calories=500,
            protein=30,
            carbs=50,
            fat=20,
        )
        test_session.commit()
        
        query = GetMealsByDateQuery(user_id="550e8400-e29b-41d4-a716-446655440001", target_date=today)
        
        # Act
        meals = await event_bus.send(query)
        
        # Assert
        assert len(meals) == 2
        meal_ids = [meal.meal_id for meal in meals]
        assert meal1_id in meal_ids
        assert meal2_id in meal_ids
        assert all(meal.status == MealStatus.READY for meal in meals)
    
    @pytest.mark.asyncio
    async def test_get_meals_by_date_empty(self, event_bus):
        """Test meals retrieval for date with no meals."""
        # Arrange
        future_date = date.today() + timedelta(days=365)
        query = GetMealsByDateQuery(user_id="550e8400-e29b-41d4-a716-446655440001", target_date=future_date)
        
        # Act
        meals = await event_bus.send(query)
        
        # Assert
        assert meals == []
    
    @pytest.mark.asyncio
    async def test_get_meals_by_date_excludes_other_dates(
        self, event_bus, test_session
    ):
        """Test that query only returns meals from specified date."""
        # Arrange
        import uuid
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        yesterday_meal_id = str(uuid.uuid4())
        today_meal_id = str(uuid.uuid4())
        
        # Create meal for yesterday
        yesterday_meal = create_test_meal_in_db(
            test_session,
            yesterday_meal_id,
            "Yesterday's Meal",
            created_at=datetime.combine(yesterday, datetime.min.time())
        )
        
        # Create meal for today
        today_meal = create_test_meal_in_db(
            test_session,
            today_meal_id,
            "Today's Meal",
            created_at=datetime.combine(today, datetime.min.time())
        )
        test_session.commit()
        
        query = GetMealsByDateQuery(user_id="550e8400-e29b-41d4-a716-446655440001", target_date=today)
        
        # Act
        meals = await event_bus.send(query)
        
        # Assert
        assert len(meals) == 1
        assert meals[0].meal_id == today_meal_id


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
            created_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=4),
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
            created_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=8),
            calories=500,
            protein=30,
            carbs=50,
            fat=20,
        )
        
        test_session.commit()
        
        query = GetDailyMacrosQuery(user_id="550e8400-e29b-41d4-a716-446655440001", target_date=today)
        
        # Act
        result = await event_bus.send(query)
        
        # Assert
        assert result["date"] == today.isoformat()
        assert result["total_calories"] == 300 + 400 + 500  # 1200
        assert result["total_protein"] == 20 + 25 + 30  # 75
        assert result["total_carbs"] == 30 + 40 + 50  # 120
        assert result["total_fat"] == 10 + 15 + 20  # 45
        assert result["meal_count"] == 3
    
    @pytest.mark.asyncio
    async def test_get_daily_macros_empty(self, event_bus):
        """Test daily macros for date with no meals."""
        # Arrange
        future_date = date.today() + timedelta(days=365)
        query = GetDailyMacrosQuery(user_id="550e8400-e29b-41d4-a716-446655440001", target_date=future_date)
        
        # Act
        result = await event_bus.send(query)
        
        # Assert
        assert result["date"] == future_date.isoformat()
        assert result["total_calories"] == 0
        assert result["total_protein"] == 0
        assert result["total_carbs"] == 0
        assert result["total_fat"] == 0
        assert result["meal_count"] == 0