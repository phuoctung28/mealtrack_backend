"""
Test data factories for creating test objects.
"""
import uuid
from datetime import datetime, date

import factory
from factory.alchemy import SQLAlchemyModelFactory
from src.infra.database.models.meal_food_item import MealFoodItem

from src.domain.model import MealStatus
from src.infra.database.models.meal import Meal as MealModel
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User


class UserFactory(SQLAlchemyModelFactory):
    """Factory for creating test users."""
    
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"
    
    user_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    email = factory.Faker("email")
    username = factory.Faker("user_name")
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class UserProfileFactory(SQLAlchemyModelFactory):
    """Factory for creating test user profiles."""
    
    class Meta:
        model = UserProfile
        sqlalchemy_session_persistence = "commit"
    
    user_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    age = factory.Faker("random_int", min=18, max=80)
    gender = factory.Faker("random_element", elements=["male", "female", "other"])
    height_cm = factory.Faker("random_int", min=150, max=200)
    weight_kg = factory.Faker("random_int", min=45, max=120)
    activity_level = factory.Faker(
        "random_element", 
        elements=["sedentary", "lightly_active", "moderately_active", "very_active", "extra_active"]
    )
    goal = factory.Faker(
        "random_element",
        elements=["lose_weight", "maintain_weight", "gain_weight"]
    )
    dietary_preferences = factory.LazyFunction(lambda: [])
    health_conditions = factory.LazyFunction(lambda: [])
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class MealFactory(SQLAlchemyModelFactory):
    """Factory for creating test meals."""
    
    class Meta:
        model = MealModel
        sqlalchemy_session_persistence = "commit"
    
    meal_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    status = MealStatus.READY.value
    dish_name = factory.Faker("word")
    created_at = factory.LazyFunction(datetime.now)
    ready_at = factory.LazyFunction(datetime.now)
    image_url = factory.Faker("image_url")
    image_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    total_calories = factory.Faker("random_int", min=100, max=1000)
    total_protein = factory.Faker("random_int", min=5, max=50)
    total_carbs = factory.Faker("random_int", min=10, max=100)
    total_fat = factory.Faker("random_int", min=5, max=40)
    confidence_score = factory.Faker("pyfloat", min_value=0.8, max_value=1.0)


class MealFoodItemFactory(SQLAlchemyModelFactory):
    """Factory for creating test meal food items."""
    
    class Meta:
        model = MealFoodItem
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: n)
    meal_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    name = factory.Faker("word")
    quantity = factory.Faker("random_int", min=50, max=300)
    unit = "g"
    calories = factory.Faker("random_int", min=50, max=500)
    protein = factory.Faker("random_int", min=0, max=40)
    carbs = factory.Faker("random_int", min=0, max=80)
    fat = factory.Faker("random_int", min=0, max=30)


class TestDataBuilder:
    """Helper class for building complex test data scenarios."""
    
    def __init__(self, session):
        self.session = session
        # Configure factories with session
        UserFactory._meta.sqlalchemy_session = session
        UserProfileFactory._meta.sqlalchemy_session = session
        MealFactory._meta.sqlalchemy_session = session
        MealFoodItemFactory._meta.sqlalchemy_session = session
    
    def create_user_with_profile(self, **kwargs):
        """Create a user with an associated profile."""
        user = UserFactory()
        profile_data = kwargs.copy()
        profile_data["user_id"] = user.user_id
        profile = UserProfileFactory(**profile_data)
        return user, profile
    
    def create_meal_with_food_items(self, num_items=3, **meal_kwargs):
        """Create a meal with associated food items."""
        meal = MealFactory(**meal_kwargs)
        food_items = []
        
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        
        for _ in range(num_items):
            item = MealFoodItemFactory(meal_id=meal.meal_id)
            food_items.append(item)
            total_calories += item.calories
            total_protein += item.protein
            total_carbs += item.carbs
            total_fat += item.fat
        
        # Update meal totals
        meal.total_calories = total_calories
        meal.total_protein = total_protein
        meal.total_carbs = total_carbs
        meal.total_fat = total_fat
        self.session.commit()
        
        return meal, food_items
    
    def create_daily_meals_for_user(self, user_id: str, meal_date: date = None):
        """Create a full day of meals for a user."""
        if meal_date is None:
            meal_date = date.today()
        
        meals = []
        meal_times = [
            ("Breakfast", 7, 300),
            ("Lunch", 12, 500),
            ("Dinner", 18, 600),
            ("Snack", 15, 200)
        ]
        
        for dish_name, hour, calories in meal_times:
            meal_datetime = datetime.combine(meal_date, datetime.min.time()).replace(hour=hour)
            meal, _ = self.create_meal_with_food_items(
                dish_name=dish_name,
                created_at=meal_datetime,
                total_calories=calories,
                user_id=user_id
            )
            meals.append(meal)
        
        return meals