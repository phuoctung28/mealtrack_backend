from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from src.domain.model.macros import Macros
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_image import MealImage
from src.domain.model.micros import Micros
from src.domain.model.nutrition import Nutrition, FoodItem
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.infra.database.config import SessionLocal
from src.infra.database.models.meal.meal import Meal as DBMeal
from src.infra.database.models.meal.meal_image import MealImage as DBMealImage
from src.infra.database.models.nutrition.nutrition import Nutrition as DBNutrition


# For development, we'll use an in-memory store
# In a real application, this would be replaced with a database
class MealRepository(MealRepositoryPort):
    """Implementation of the meal repository using SQLAlchemy."""
    
    def __init__(self, db: Session = None):
        """Initialize with optional session dependency."""
        self.db = db
    
    def _get_db(self):
        """Get a database session, creating one if needed."""
        if self.db:
            return self.db
        else:
            return SessionLocal()
    
    def _close_db_if_created(self, db):
        """Close the database session if we created it."""
        if self.db is None and db is not None:
            db.close()
    
    def save(self, meal: Meal) -> Meal:
        """Save a meal to the database."""
        db = self._get_db()
        
        try:
            # Check if meal already exists
            existing_meal = db.query(DBMeal).filter(DBMeal.meal_id == meal.meal_id).first()
            
            if existing_meal:
                # Update existing meal
                from src.domain.model.meal import MealStatus
                
                # Handle nutrition data
                if meal.nutrition and not existing_meal.nutrition:
                    # Create new nutrition
                    db_nutrition = DBNutrition.from_domain(meal.nutrition, meal_id=meal.meal_id)
                    existing_meal.nutrition = db_nutrition
                elif meal.nutrition and existing_meal.nutrition:
                    # Update existing nutrition - this would be more complex in a real app
                    # For now, we'll just delete and recreate
                    db.delete(existing_meal.nutrition)
                    db.flush()
                    db_nutrition = DBNutrition.from_domain(meal.nutrition, meal_id=meal.meal_id)
                    existing_meal.nutrition = db_nutrition
                
                # Update other fields
                from src.infra.database.models.enums import MealStatusEnum
                status_mapping = {
                    MealStatus.PROCESSING: MealStatusEnum.PROCESSING,
                    MealStatus.ANALYZING: MealStatusEnum.ANALYZING, 
                    MealStatus.ENRICHING: MealStatusEnum.ENRICHING,
                    MealStatus.READY: MealStatusEnum.READY,
                    MealStatus.FAILED: MealStatusEnum.FAILED,
                }
                
                existing_meal.status = status_mapping[meal.status]
                existing_meal.dish_name = getattr(meal, "dish_name", None)
                existing_meal.ready_at = getattr(meal, "ready_at", None)
                existing_meal.error_message = getattr(meal, "error_message", None)
                existing_meal.raw_ai_response = getattr(meal, "raw_gpt_json", None)
                
                db.commit()
                return meal
            else:
                # Create new meal
                db_meal = DBMeal.from_domain(meal)
                
                # Check if image exists
                existing_image = db.query(DBMealImage).filter(
                    DBMealImage.image_id == meal.image.image_id
                ).first()
                
                if not existing_image:
                    db_image = DBMealImage.from_domain(meal.image)
                    db.add(db_image)
                
                db.add(db_meal)
                db.commit()
                return meal
        except Exception as e:
            db.rollback()
            raise e
        finally:
            self._close_db_if_created(db)
    
    def find_by_id(self, meal_id: str) -> Optional[Meal]:
        """Find a meal by ID."""
        db = self._get_db()
        
        try:
            db_meal = db.query(DBMeal).filter(DBMeal.meal_id == meal_id).first()
            
            if db_meal:
                return db_meal.to_domain()
            else:
                return None
        finally:
            self._close_db_if_created(db)
    
    def find_by_status(self, status: MealStatus, limit: int = 10) -> List[Meal]:
        """Find meals by status."""
        db = self._get_db()
        
        try:
            from src.infra.database.models.enums import MealStatusEnum
            
            status_mapping = {
                MealStatus.PROCESSING: MealStatusEnum.PROCESSING,
                MealStatus.ANALYZING: MealStatusEnum.ANALYZING,
                MealStatus.ENRICHING: MealStatusEnum.ENRICHING,
                MealStatus.READY: MealStatusEnum.READY,
                MealStatus.FAILED: MealStatusEnum.FAILED,
            }
            
            db_meals = (
                db.query(DBMeal)
                .filter(DBMeal.status == status_mapping[status])
                .order_by(DBMeal.created_at)  # Oldest first
                .limit(limit)
                .all()
            )
            
            return [meal.to_domain() for meal in db_meals]
        finally:
            self._close_db_if_created(db)
    
    def delete(self, meal_id: str) -> bool:
        """Delete a meal by ID."""
        db = self._get_db()
        
        try:
            db_meal = db.query(DBMeal).filter(DBMeal.meal_id == meal_id).first()
            
            if db_meal:
                db.delete(db_meal)
                db.commit()
                return True
            else:
                return False
        except Exception as e:
            db.rollback()
            raise e
        finally:
            self._close_db_if_created(db)
    
    def find_all_paginated(self, offset: int = 0, limit: int = 20) -> List[Meal]:
        """
        Retrieves all meals with pagination.
        
        Args:
            offset: Pagination offset
            limit: Maximum number of results
            
        Returns:
            Paginated list of meals
        """
        all_meals = list(self._meals.values())
        all_meals.sort(key=lambda m: m["created_at"], reverse=True)  # Newest first
        
        paginated_meals = all_meals[offset:offset + limit]
        return [self._meal_from_dict(meal_dict) for meal_dict in paginated_meals]
    
    def count(self) -> int:
        """
        Counts the total number of meals.
        
        Returns:
            Total count
        """
        return len(self._meals)
    
    def find_by_date(self, date, user_id: str = None, limit: int = 50) -> List[Meal]:
        """Find meals created on a specific date, optionally filtered by user."""
        db = self._get_db()
        
        try:
            from datetime import datetime, timedelta
            
            # Create start and end datetime for the date range
            start_datetime = datetime.combine(date, datetime.min.time())
            end_datetime = start_datetime + timedelta(days=1)
            
            # Query meals created within the date range
            query = (
                db.query(DBMeal)
                .filter(DBMeal.created_at >= start_datetime)
                .filter(DBMeal.created_at < end_datetime)
            )
            
            # Add user filter if provided
            if user_id:
                query = query.filter(DBMeal.user_id == user_id)
            
            db_meals = (
                query
                .order_by(DBMeal.created_at.desc())  # Newest first
                .limit(limit)
                .all()
            )
            
            return [meal.to_domain() for meal in db_meals]
        finally:
            self._close_db_if_created(db)
    
    def _meal_from_dict(self, data: Dict[str, Any]) -> Meal:
        """Convert dictionary representation back to Meal object."""
        # Create MealImage
        image_data = data["image"]
        image = MealImage(
            image_id=image_data["image_id"],
            format=image_data["format"],
            size_bytes=image_data["size_bytes"],
            width=image_data.get("width"),
            height=image_data.get("height"),
            url=image_data.get("url")
        )
        
        # Process nutrition if available
        nutrition = None
        if "nutrition" in data:
            nutrition_data = data["nutrition"]
            
            # Create Macros
            macros = Macros(
                protein=nutrition_data["macros"]["protein_g"],
                carbs=nutrition_data["macros"]["carbs_g"],
                fat=nutrition_data["macros"]["fat_g"],
                fiber=nutrition_data["macros"].get("fiber_g")
            )
            
            # Create Micros if available
            micros = None
            if "micros" in nutrition_data:
                micros = Micros.from_dict(nutrition_data["micros"])
            
            # Create FoodItems if available
            food_items = None
            if "food_items" in nutrition_data:
                food_items = []
                for item_data in nutrition_data["food_items"]:
                    item_macros = Macros(
                        protein=item_data["macros"]["protein_g"],
                        carbs=item_data["macros"]["carbs_g"],
                        fat=item_data["macros"]["fat_g"],
                        fiber=item_data["macros"].get("fiber_g")
                    )
                    
                    item_micros = None
                    if "micros" in item_data:
                        item_micros = Micros.from_dict(item_data["micros"])
                        
                    food_item = FoodItem(
                        name=item_data["name"],
                        quantity=item_data["quantity"],
                        unit=item_data["unit"],
                        calories=item_data["calories"],
                        macros=item_macros,
                        micros=item_micros,
                        confidence=item_data["confidence"]
                    )
                    food_items.append(food_item)
            
            # Create Nutrition
            nutrition = Nutrition(
                calories=nutrition_data["calories"],
                macros=macros,
                micros=micros,
                food_items=food_items,
                confidence_score=nutrition_data["confidence_score"]
            )
        
        # Create Meal
        return Meal(
            meal_id=data["meal_id"],
            user_id=data["user_id"],
            status=MealStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            image=image,
            nutrition=nutrition,
            ready_at=datetime.fromisoformat(data["ready_at"]) if "ready_at" in data else None,
            error_message=data.get("error_message"),
            raw_gpt_json=data.get("raw_gpt_json")
        ) 