import logging
from typing import List, Optional
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session, joinedload, selectinload

from src.domain.model.meal import Meal, MealStatus
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.infra.database.models.meal.meal import Meal as DBMeal
from src.infra.database.models.meal.meal_image import MealImage as DBMealImage
from src.infra.database.models.nutrition.nutrition import Nutrition as DBNutrition
from src.infra.database.models.nutrition.food_item import FoodItem as DBFoodItem
from src.infra.mappers.meal_mapper import MealMapper, MealImageMapper, NutritionMapper, FoodItemMapper
from src.infra.mappers import MealStatusMapper
from src.infra.database.models.enums import MealStatusEnum

logger = logging.getLogger(__name__)

_MEAL_LOAD_OPTIONS = (
    joinedload(DBMeal.image),
    selectinload(DBMeal.nutrition).selectinload(DBNutrition.food_items),
)


class MealRepository(MealRepositoryPort):
    """Implementation of the meal repository using SQLAlchemy."""
    
    def __init__(self, db: Session):
        """Initialize with session dependency."""
        self.db = db
    
    def save(self, meal: Meal) -> Meal:
        """Save a meal to the database."""
        try:
            # Check if meal already exists
            existing_meal = self.db.query(DBMeal).filter(DBMeal.meal_id == meal.meal_id).first()
            
            if existing_meal:
                # Update existing meal
                # Update scalar fields
                existing_meal.status = MealStatusMapper.to_db(meal.status)
                existing_meal.dish_name = meal.dish_name
                existing_meal.ready_at = meal.ready_at
                existing_meal.error_message = meal.error_message
                existing_meal.raw_ai_response = meal.raw_gpt_json
                existing_meal.updated_at = meal.updated_at or datetime.utcnow()
                existing_meal.last_edited_at = meal.last_edited_at
                existing_meal.edit_count = meal.edit_count
                existing_meal.is_manually_edited = meal.is_manually_edited

                # Handle nutrition sync
                if meal.nutrition:
                    if not existing_meal.nutrition:
                        # Create new nutrition
                        db_nutrition = NutritionMapper.to_persistence(meal.nutrition, meal_id=meal.meal_id)
                        existing_meal.nutrition = db_nutrition
                        # Flush to get nutrition ID before creating food_items
                        self.db.flush()
                        # Add food items
                        if meal.nutrition.food_items:
                            for item in meal.nutrition.food_items:
                                db_item = FoodItemMapper.to_persistence(item, nutrition_id=db_nutrition.id)
                                self.db.add(db_item)
                    else:
                        # Update existing nutrition
                        self._update_nutrition(existing_meal.nutrition, meal.nutrition)
                
                self.db.commit()
                # Return refreshed domain object
                return MealMapper.to_domain(existing_meal)
            else:
                # Create new meal
                db_meal = MealMapper.to_persistence(meal)
                
                # Handle Image
                existing_image = self.db.query(DBMealImage).filter(
                    DBMealImage.image_id == meal.image.image_id
                ).first()
                
                if not existing_image:
                    db_image = MealImageMapper.to_persistence(meal.image)
                    self.db.add(db_image)
                else:
                    db_meal.image_id = existing_image.image_id # Link to existing image
                
                self.db.add(db_meal)
                
                # Handle Nutrition if present
                if meal.nutrition:
                    db_nutrition = NutritionMapper.to_persistence(meal.nutrition, meal_id=meal.meal_id)
                    self.db.add(db_nutrition)
                    # Flush to get nutrition ID before creating food_items
                    self.db.flush()
                    # Add food items
                    if meal.nutrition.food_items:
                        for item in meal.nutrition.food_items:
                            db_item = FoodItemMapper.to_persistence(item, nutrition_id=db_nutrition.id)
                            self.db.add(db_item)
                
                # Note: The above logic for nutrition creation in `save` (insert case) is simplified.
                # Since we are using SQLAlchemy ORM, if we set relationships on `db_meal`, 
                # SQLAlchemy should handle it IF we construct the object graph correctly.
                # But `MealMapper.to_persistence` doesn't set relationships.
                # So we must set them manually here or update Mapper.
                
                # Let's retry:
                # `db_meal` is created.
                if meal.image:
                     db_meal.image_id = str(meal.image.image_id)

                if meal.nutrition:
                     # This logic is tricky without flushing.
                     # Let's trust that we can add DBNutrition separately.
                     pass 

                self.db.commit()
                self.db.refresh(db_meal)
                return MealMapper.to_domain(db_meal)

        except Exception as e:
            self.db.rollback()
            raise e
    
    def find_by_id(self, meal_id: str) -> Optional[Meal]:
        """Find a meal by ID."""
        db_meal = (
            self.db.query(DBMeal)
            .options(*_MEAL_LOAD_OPTIONS)
            .filter(DBMeal.meal_id == meal_id)
            .first()
        )
        return MealMapper.to_domain(db_meal) if db_meal else None
    
    def find_by_status(self, status: MealStatus, limit: int = 10) -> List[Meal]:
        """Find meals by status."""
        db_meals = (
            self.db.query(DBMeal)
            .options(*_MEAL_LOAD_OPTIONS)
            .filter(DBMeal.status == MealStatusMapper.to_db(status))
            .order_by(DBMeal.created_at)
            .limit(limit)
            .all()
        )
        return [MealMapper.to_domain(m) for m in db_meals]
    
    def delete(self, meal_id: str) -> bool:
        """Delete a meal by ID."""
        try:
            db_meal = self.db.query(DBMeal).filter(DBMeal.meal_id == meal_id).first()
            if db_meal:
                self.db.delete(db_meal)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            raise e
    
    def find_all_paginated(self, offset: int = 0, limit: int = 20) -> List[Meal]:
        """Retrieves all meals with pagination."""
        db_meals = (
            self.db.query(DBMeal)
            .options(*_MEAL_LOAD_OPTIONS)
            .order_by(DBMeal.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [MealMapper.to_domain(m) for m in db_meals]
    
    def count(self) -> int:
        """Counts the total number of meals."""
        return self.db.query(DBMeal).count()
    
    def find_by_date(self, date_obj: date, user_id: str = None, limit: int = 50) -> List[Meal]:
        """Find meals created on a specific date."""
        start_datetime = datetime.combine(date_obj, datetime.min.time())
        end_datetime = start_datetime + timedelta(days=1)
        
        query = (
            self.db.query(DBMeal)
            .options(*_MEAL_LOAD_OPTIONS)
            .filter(DBMeal.created_at >= start_datetime)
            .filter(DBMeal.created_at < end_datetime)
        )
        
        if user_id:
            query = query.filter(DBMeal.user_id == user_id)
        
        db_meals = (
            query
            .filter(DBMeal.status != MealStatusEnum.INACTIVE)
            .order_by(DBMeal.created_at.desc())
            .limit(limit)
            .all()
        )
        return [MealMapper.to_domain(m) for m in db_meals]

    def _update_nutrition(self, db_nutrition: DBNutrition, domain_nutrition: Meal.nutrition):
        """Helper to sync nutrition data."""
        # Update scalar fields
        db_nutrition.calories = domain_nutrition.calories
        db_nutrition.protein = domain_nutrition.macros.protein
        db_nutrition.carbs = domain_nutrition.macros.carbs
        db_nutrition.fat = domain_nutrition.macros.fat
        db_nutrition.confidence_score = domain_nutrition.confidence_score
        
        # Sync food items (Simplified: Delete all and re-create is easier/safer if IDs not persistent)
        # But we want to preserve IDs if possible.
        
        # Get existing items
        existing_items = {item.id: item for item in db_nutrition.food_items} if db_nutrition.food_items else {}
        
        # Domain items don't strictly match DB items by ID unless we enforce it.
        # But domain `FoodItem` doesn't seem to have `id` in `to_domain`?
        # Let's check `FoodItemMapper`.
        
        # In `MealMapper.py`, `FoodItemMapper.to_domain` does NOT map ID!
        # Because `FoodItem` domain model might not have an ID?
        # Let's check `src/domain/model/nutrition/nutrition.py`.
        
        # If FoodItem has no ID in domain, we can't reliably update. We must replace.
        
        # Delete old items
        for item in db_nutrition.food_items:
            self.db.delete(item)
            
        # Add new items
        if domain_nutrition.food_items:
            for item in domain_nutrition.food_items:
                db_item = FoodItemMapper.to_persistence(item, nutrition_id=db_nutrition.id)
                self.db.add(db_item)