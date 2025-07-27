"""
Command handlers for meal domain - write operations.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from src.api.exceptions import ValidationException, ResourceNotFoundException
from src.app.commands.meal import (
    UploadMealImageCommand,
    RecalculateMealNutritionCommand
)
from src.app.events.base import EventHandler, handles
from src.app.events.meal import (
    MealImageUploadedEvent,
    MealNutritionUpdatedEvent
)
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_image import MealImage
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort

logger = logging.getLogger(__name__)


@handles(UploadMealImageCommand)
class UploadMealImageCommandHandler(EventHandler[UploadMealImageCommand, Dict[str, Any]]):
    """Handler for uploading meal images."""
    
    def __init__(self, meal_repository: MealRepositoryPort = None, image_store: ImageStorePort = None):
        self.meal_repository = meal_repository
        self.image_store = image_store
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.image_store = kwargs.get('image_store', self.image_store)
    
    async def handle(self, command: UploadMealImageCommand) -> Dict[str, Any]:
        """Upload meal image and create meal record."""
        if not self.meal_repository or not self.image_store:
            raise RuntimeError("Dependencies not configured")
        
        # Upload image
        image_id = self.image_store.save(
            command.file_contents,
            command.content_type
        )
        
        # Get image URL
        image_url = self.image_store.get_url(image_id)
        
        # Create meal image
        meal_image = MealImage(
            image_id=image_id,
            format="jpeg" if command.content_type == "image/jpeg" else "png",
            size_bytes=len(command.file_contents),
            url=image_url or f"mock://images/{image_id}"
        )
        
        # Create meal
        meal = Meal(
            meal_id=str(uuid4()),
            status=MealStatus.PROCESSING,
            created_at=datetime.now(),
            image=meal_image
        )
        
        # Save meal
        saved_meal = self.meal_repository.save(meal)
        
        return {
            "meal_id": saved_meal.meal_id,
            "status": saved_meal.status.value,
            "image_url": saved_meal.image.url if saved_meal.image else None,
            "events": [
                MealImageUploadedEvent(
                    aggregate_id=saved_meal.meal_id,
                    meal_id=saved_meal.meal_id,
                    image_url=meal_image.url,
                    upload_timestamp=datetime.now()
                )
            ]
        }


@handles(RecalculateMealNutritionCommand)
class RecalculateMealNutritionCommandHandler(EventHandler[RecalculateMealNutritionCommand, Dict[str, Any]]):
    """Handler for recalculating meal nutrition based on weight."""
    
    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
    
    async def handle(self, command: RecalculateMealNutritionCommand) -> Dict[str, Any]:
        """Recalculate meal nutrition based on new weight."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")
        
        # Validate weight
        if command.weight_grams <= 0:
            raise ValidationException("Weight must be greater than 0")
        
        # Get meal
        meal = self.meal_repository.find_by_id(command.meal_id)
        if not meal:
            raise ResourceNotFoundException(f"Meal with ID {command.meal_id} not found")
        
        if not meal.nutrition:
            raise ValidationException(f"Meal {command.meal_id} has no nutrition data to recalculate")
        
        # Calculate scale factor
        # Assume original portion was 100g if not specified
        old_weight = getattr(meal, 'weight_grams', 100.0)
        scale_factor = command.weight_grams / old_weight
        
        # Update nutrition values directly (since we made them mutable)
        meal.nutrition.calories = meal.nutrition.calories * scale_factor
        meal.nutrition.macros.protein = meal.nutrition.macros.protein * scale_factor
        meal.nutrition.macros.carbs = meal.nutrition.macros.carbs * scale_factor
        meal.nutrition.macros.fat = meal.nutrition.macros.fat * scale_factor
        
        if hasattr(meal.nutrition.macros, 'fiber') and meal.nutrition.macros.fiber:
            meal.nutrition.macros.fiber = meal.nutrition.macros.fiber * scale_factor
        
        # Update food items if present
        if meal.nutrition.food_items:
            for item in meal.nutrition.food_items:
                item.quantity = item.quantity * scale_factor
                item.calories = item.calories * scale_factor
                item.macros.protein = item.macros.protein * scale_factor
                item.macros.carbs = item.macros.carbs * scale_factor
                item.macros.fat = item.macros.fat * scale_factor
                if item.macros.fiber:
                    item.macros.fiber = item.macros.fiber * scale_factor
        
        # Save updated meal
        updated_meal = self.meal_repository.save(meal)
        
        # Prepare nutrition data for response
        nutrition_data = {
            "calories": round(updated_meal.nutrition.calories, 1),
            "protein": round(updated_meal.nutrition.macros.protein, 1),
            "carbs": round(updated_meal.nutrition.macros.carbs, 1),
            "fat": round(updated_meal.nutrition.macros.fat, 1)
        }
        
        if hasattr(updated_meal.nutrition, 'fiber') and updated_meal.nutrition.fiber:
            nutrition_data["fiber"] = round(updated_meal.nutrition.fiber, 1)
        
        return {
            "meal_id": command.meal_id,
            "updated_nutrition": nutrition_data,
            "weight_grams": command.weight_grams,
            "events": [
                MealNutritionUpdatedEvent(
                    aggregate_id=command.meal_id,
                    meal_id=command.meal_id,
                    old_weight=old_weight,
                    new_weight=command.weight_grams,
                    updated_nutrition=nutrition_data
                )
            ]
        }