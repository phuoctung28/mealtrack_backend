"""
Factory for creating test meals.
"""
from uuid import uuid4
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from src.infra.database.models.meal.meal import Meal
from src.infra.database.models.meal.meal_image import MealImage
from src.infra.database.models.nutrition.nutrition import Nutrition
from src.infra.database.models.nutrition.food_item import FoodItem
from src.infra.database.models.enums import MealStatusEnum
from tests.fixtures.factories.nutrition_factory import NutritionFactory


class MealFactory:
    """Factory for creating test meals."""
    
    @staticmethod
    def create_meal(session: Session, user_id: str, **overrides) -> Meal:
        """
        Create a meal with nutrition data.
        
        Args:
            session: Database session
            user_id: User ID for the meal
            **overrides: Override any default meal attributes
            
        Returns:
            Meal: Created meal instance
        """
        meal_id = str(uuid4())
        image_id = str(uuid4())
        
        # Create meal image
        image = MealImage(
            image_id=image_id,
            format="jpeg",
            size_bytes=102400,
            width=1920,
            height=1080,
            url=f"https://test-image-url.com/{image_id}.jpg",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(image)
        session.flush()
        
        # Create meal
        meal_defaults = {
            "meal_id": meal_id,
            "user_id": user_id,
            "image_id": image_id,
            "status": MealStatusEnum.READY,
            "dish_name": "Grilled Chicken with Rice",
            "ready_at": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        meal_defaults.update(overrides)
        
        meal = Meal(**meal_defaults)
        session.add(meal)
        session.flush()
        
        # Create nutrition
        nutrition = Nutrition(
            meal_id=meal_id,
            calories=560.0,
            protein=45.0,
            carbs=50.0,
            fat=12.0,
            confidence_score=0.95,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(nutrition)
        session.flush()
        
        # Create food items
        food_items_data = [
            {"name": "Chicken Breast", "quantity": 200.0, "unit": "g", "calories": 330.0, "protein": 62.0, "carbs": 0.0, "fat": 7.0},
            {"name": "Rice", "quantity": 150.0, "unit": "g", "calories": 195.0, "protein": 4.5, "carbs": 40.0, "fat": 0.6},
            {"name": "Broccoli", "quantity": 100.0, "unit": "g", "calories": 35.0, "protein": 2.8, "carbs": 7.0, "fat": 0.4},
        ]
        
        for item_data in food_items_data:
            food_item = FoodItem(
                id=str(uuid4()),
                name=item_data["name"],
                quantity=item_data["quantity"],
                unit=item_data["unit"],
                calories=item_data["calories"],
                protein=item_data["protein"],
                carbs=item_data["carbs"],
                fat=item_data["fat"],
                nutrition_id=nutrition.id,
                confidence=0.95,
                is_custom=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(food_item)
        
        session.commit()
        return meal
    
    @staticmethod
    def create_manual_meal(
        session: Session,
        user_id: str,
        foods: List[dict],
        **overrides
    ) -> Meal:
        """
        Create manual meal from food list.
        
        Args:
            session: Database session
            user_id: User ID for the meal
            foods: List of food dictionaries with name, quantity, unit, etc.
            **overrides: Override any default meal attributes
            
        Returns:
            Meal: Created meal instance
        """
        meal_id = str(uuid4())
        image_id = str(uuid4())
        
        # Create meal image (optional for manual meals)
        image = MealImage(
            image_id=image_id,
            format="jpeg",
            size_bytes=0,
            url=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(image)
        session.flush()
        
        # Create meal
        meal_defaults = {
            "meal_id": meal_id,
            "user_id": user_id,
            "image_id": image_id,
            "status": MealStatusEnum.READY,
            "dish_name": "Manual Meal",
            "ready_at": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        meal_defaults.update(overrides)
        
        meal = Meal(**meal_defaults)
        session.add(meal)
        session.flush()
        
        # Calculate total nutrition from foods
        total_calories = sum(food.get("calories", 0) for food in foods)
        total_protein = sum(food.get("protein", 0) for food in foods)
        total_carbs = sum(food.get("carbs", 0) for food in foods)
        total_fat = sum(food.get("fat", 0) for food in foods)
        
        # Create nutrition
        nutrition = Nutrition(
            meal_id=meal_id,
            calories=total_calories,
            protein=total_protein,
            carbs=total_carbs,
            fat=total_fat,
            confidence_score=1.0,  # Manual meals have 100% confidence
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(nutrition)
        session.flush()
        
        # Create food items from foods list
        for food_data in foods:
            food_item = FoodItem(
                id=str(uuid4()),
                name=food_data.get("name", "Unknown Food"),
                quantity=food_data.get("quantity", 100.0),
                unit=food_data.get("unit", "g"),
                calories=food_data.get("calories", 0.0),
                protein=food_data.get("protein", 0.0),
                carbs=food_data.get("carbs", 0.0),
                fat=food_data.get("fat", 0.0),
                nutrition_id=nutrition.id,
                confidence=1.0,
                is_custom=food_data.get("is_custom", False),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(food_item)
        
        session.commit()
        return meal
