"""
Integration tests for meal query handlers.
"""
import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from src.app.queries.meal import (
    GetMealByIdQuery,
    GetMealsByDateQuery,
    GetDailyMacrosQuery
)
from src.domain.model.meal import MealStatus
from src.infra.database.models.meal import Meal as MealModel
from src.api.exceptions import ResourceNotFoundException


@pytest.mark.integration
class TestGetMealByIdQueryHandler:
    """Test GetMealByIdQuery handler with database."""
    
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
        assert meal.nutrition.calories == sample_meal_db.total_calories
    
    async def test_get_meal_by_id_not_found(self, event_bus):
        """Test meal retrieval with non-existent ID."""
        # Arrange
        query = GetMealByIdQuery(meal_id="non-existent-meal")
        
        # Act & Assert
        with pytest.raises(ResourceNotFoundException):
            await event_bus.send(query)
    
    async def test_get_meal_by_id_with_food_items(
        self, event_bus, test_session, sample_meal_domain
    ):
        """Test meal retrieval includes food items."""
        # Arrange - Create meal with food items
        from src.infra.database.models.meal_food_item import MealFoodItem
        meal_model = MealModel(
            meal_id="meal-with-items",
            status=MealStatus.READY.value,
            dish_name="Test Meal with Items",
            created_at=datetime.now(),
            image_url="https://example.com/image.jpg",
            image_id="image-123",
            total_calories=500,
            total_protein=30,
            total_carbs=50,
            total_fat=20,
            total_fiber=5
        )
        test_session.add(meal_model)
        
        # Add food items
        food_item1 = MealFoodItem(
            meal_id="meal-with-items",
            name="Rice",
            quantity=150,
            unit="g",
            calories=200,
            protein=5,
            carbs=40,
            fat=2,
            fiber=2
        )
        food_item2 = MealFoodItem(
            meal_id="meal-with-items",
            name="Chicken",
            quantity=100,
            unit="g",
            calories=300,
            protein=25,
            carbs=10,
            fat=18,
            fiber=3
        )
        test_session.add(food_item1)
        test_session.add(food_item2)
        test_session.commit()
        
        query = GetMealByIdQuery(meal_id="meal-with-items")
        
        # Act
        meal = await event_bus.send(query)
        
        # Assert
        assert meal.meal_id == "meal-with-items"
        assert meal.nutrition is not None
        assert len(meal.nutrition.food_items) == 2
        assert meal.nutrition.food_items[0].name == "Rice"
        assert meal.nutrition.food_items[1].name == "Chicken"


@pytest.mark.integration
class TestGetMealsByDateQueryHandler:
    """Test GetMealsByDateQuery handler with database."""
    
    async def test_get_meals_by_date_success(self, event_bus, test_session):
        """Test successful meals retrieval by date."""
        # Arrange - Create meals for today
        today = date.today()
        meal1 = MealModel(
            meal_id="meal-today-1",
            status=MealStatus.READY.value,
            dish_name="Breakfast",
            created_at=datetime.combine(today, datetime.min.time()),
            image_url="https://example.com/breakfast.jpg",
            image_id="breakfast-123",
            total_calories=300,
            total_protein=20,
            total_carbs=30,
            total_fat=10,
            total_fiber=5
        )
        meal2 = MealModel(
            meal_id="meal-today-2",
            status=MealStatus.READY.value,
            dish_name="Lunch",
            created_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=4),
            image_url="https://example.com/lunch.jpg",
            image_id="lunch-123",
            total_calories=500,
            total_protein=30,
            total_carbs=50,
            total_fat=20,
            total_fiber=8
        )
        test_session.add(meal1)
        test_session.add(meal2)
        test_session.commit()
        
        query = GetMealsByDateQuery(date=today)
        
        # Act
        meals = await event_bus.send(query)
        
        # Assert
        assert len(meals) == 2
        assert meals[0].meal_id == "meal-today-1"
        assert meals[1].meal_id == "meal-today-2"
        assert all(meal.status == MealStatus.READY for meal in meals)
    
    async def test_get_meals_by_date_empty(self, event_bus):
        """Test meals retrieval for date with no meals."""
        # Arrange
        future_date = date.today() + timedelta(days=365)
        query = GetMealsByDateQuery(date=future_date)
        
        # Act
        meals = await event_bus.send(query)
        
        # Assert
        assert meals == []
    
    async def test_get_meals_by_date_excludes_other_dates(
        self, event_bus, test_session
    ):
        """Test that query only returns meals from specified date."""
        # Arrange
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Create meal for yesterday
        yesterday_meal = MealModel(
            meal_id="meal-yesterday",
            status=MealStatus.READY.value,
            dish_name="Yesterday's Meal",
            created_at=datetime.combine(yesterday, datetime.min.time()),
            image_url="https://example.com/yesterday.jpg",
            image_id="yesterday-123",
            total_calories=400,
            total_protein=25,
            total_carbs=40,
            total_fat=15,
            total_fiber=6
        )
        
        # Create meal for today
        today_meal = MealModel(
            meal_id="meal-today",
            status=MealStatus.READY.value,
            dish_name="Today's Meal",
            created_at=datetime.combine(today, datetime.min.time()),
            image_url="https://example.com/today.jpg",
            image_id="today-123",
            total_calories=450,
            total_protein=28,
            total_carbs=45,
            total_fat=18,
            total_fiber=7
        )
        
        test_session.add(yesterday_meal)
        test_session.add(today_meal)
        test_session.commit()
        
        query = GetMealsByDateQuery(date=today)
        
        # Act
        meals = await event_bus.send(query)
        
        # Assert
        assert len(meals) == 1
        assert meals[0].meal_id == "meal-today"


@pytest.mark.integration
class TestGetDailyMacrosQueryHandler:
    """Test GetDailyMacrosQuery handler with database."""
    
    async def test_get_daily_macros_success(self, event_bus, test_session):
        """Test successful daily macros calculation."""
        # Arrange - Create multiple meals for today
        today = date.today()
        meals = [
            MealModel(
                meal_id=f"meal-{i}",
                status=MealStatus.READY.value,
                dish_name=f"Meal {i}",
                created_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=i*4),
                image_url=f"https://example.com/meal{i}.jpg",
                image_id=f"meal-{i}-123",
                total_calories=300 + i*100,
                total_protein=20 + i*5,
                total_carbs=30 + i*10,
                total_fat=10 + i*5,
                total_fiber=5 + i
            )
            for i in range(3)
        ]
        
        for meal in meals:
            test_session.add(meal)
        test_session.commit()
        
        query = GetDailyMacrosQuery(date=today)
        
        # Act
        result = await event_bus.send(query)
        
        # Assert
        assert result["date"] == today
        assert result["total_calories"] == 300 + 400 + 500  # 1200
        assert result["total_protein"] == 20 + 25 + 30  # 75
        assert result["total_carbs"] == 30 + 40 + 50  # 120
        assert result["total_fat"] == 10 + 15 + 20  # 45
        assert result["total_fiber"] == 5 + 6 + 7  # 18
        assert result["meal_count"] == 3
    
    async def test_get_daily_macros_empty(self, event_bus):
        """Test daily macros for date with no meals."""
        # Arrange
        future_date = date.today() + timedelta(days=365)
        query = GetDailyMacrosQuery(date=future_date)
        
        # Act
        result = await event_bus.send(query)
        
        # Assert
        assert result["date"] == future_date
        assert result["total_calories"] == 0
        assert result["total_protein"] == 0
        assert result["total_carbs"] == 0
        assert result["total_fat"] == 0
        assert result["total_fiber"] == 0
        assert result["meal_count"] == 0