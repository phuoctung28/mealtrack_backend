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
    RecalculateMealNutritionCommand,
    AnalyzeMealImageCommand
)
from src.app.events.base import EventHandler, handles
from src.app.events.meal import (
    MealImageUploadedEvent,
    MealNutritionUpdatedEvent,
    MealAnalysisStartedEvent
)
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_image import MealImage
from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort

# from src.app.jobs.analyse_meal_image_job import analyse_meal_image_job  # TODO: Implement background jobs

logger = logging.getLogger(__name__)


@handles(UploadMealImageCommand)
class UploadMealImageCommandHandler(EventHandler[UploadMealImageCommand, Dict[str, Any]]):
    """Handler for uploading and storing meal images."""
    
    def __init__(
        self,
        image_store: ImageStorePort = None,
        meal_repository: MealRepositoryPort = None,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None
    ):
        self.image_store = image_store
        self.meal_repository = meal_repository
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.image_store = kwargs.get('image_store', self.image_store)
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.vision_service = kwargs.get('vision_service', self.vision_service)
        self.gpt_parser = kwargs.get('gpt_parser', self.gpt_parser)
    
    async def handle(self, command: UploadMealImageCommand) -> Dict[str, Any]:
        """Handle meal image upload."""
        if not all([self.image_store, self.meal_repository]):
            raise RuntimeError("Required dependencies not configured")
        
        # Upload image to storage
        image_url = self.image_store.save(
            command.file_contents,
            command.content_type
        )
        
        # Create meal record
        meal = Meal(
            meal_id=str(uuid4()),
            status=MealStatus.PROCESSING,
            created_at=datetime.now(),
            image=MealImage(
                image_id=str(uuid4()),
                format="jpeg",  # Default format
                size_bytes=len(command.file_contents),
                url=image_url
            )
        )
        
        # Save meal
        saved_meal = self.meal_repository.save(meal)
        
        # Return result with events
        return {
            "meal_id": saved_meal.meal_id,
            "status": saved_meal.status.value,
            "image_url": image_url,
            "events": [
                MealImageUploadedEvent(
                    aggregate_id=saved_meal.meal_id,
                    meal_id=saved_meal.meal_id,
                    image_url=image_url,
                    upload_timestamp=datetime.now()
                )
            ]
        }


@handles(RecalculateMealNutritionCommand)
class RecalculateMealNutritionCommandHandler(EventHandler[RecalculateMealNutritionCommand, Dict[str, Any]]):
    """Handler for recalculating meal nutrition based on weight."""
    
    def __init__(self, meal_repository: MealRepositoryPort = None):
        self.meal_repository = meal_repository
    
    def set_dependencies(self, meal_repository: MealRepositoryPort):
        """Set dependencies for dependency injection."""
        self.meal_repository = meal_repository
    
    async def handle(self, command: RecalculateMealNutritionCommand) -> Dict[str, Any]:
        """Recalculate meal nutrition with new weight."""
        if not self.meal_repository:
            raise RuntimeError("Meal repository not configured")
        
        if command.weight_grams <= 0:
            raise ValidationException("Weight must be greater than 0")
        
        # Get meal
        meal = self.meal_repository.find_by_id(command.meal_id)
        if not meal:
            raise ResourceNotFoundException(f"Meal with ID {command.meal_id} not found")
        
        if not meal.nutrition:
            raise ValidationException(f"Meal {command.meal_id} has no nutrition data to recalculate")
        
        # Store old weight for event
        old_weight = getattr(meal, 'weight_grams', 100.0)
        
        # Calculate scaling factor
        original_weight = 100.0  # Assuming original calculations were per 100g
        scale_factor = command.weight_grams / original_weight
        
        # Update nutrition values
        meal.nutrition.calories = meal.nutrition.calories * scale_factor
        meal.nutrition.protein = meal.nutrition.protein * scale_factor
        meal.nutrition.carbs = meal.nutrition.carbs * scale_factor
        meal.nutrition.fat = meal.nutrition.fat * scale_factor
        if hasattr(meal.nutrition, 'fiber') and meal.nutrition.fiber:
            meal.nutrition.fiber = meal.nutrition.fiber * scale_factor
        
        # Update food items if present
        if meal.nutrition.food_items:
            for item in meal.nutrition.food_items:
                item.calories = item.calories * scale_factor
                if hasattr(item, 'quantity'):
                    item.quantity = item.quantity * scale_factor
        
        # Store the new weight
        meal.weight_grams = command.weight_grams
        
        # Save updated meal
        updated_meal = self.meal_repository.save(meal)
        
        # Prepare nutrition data for response
        nutrition_data = {
            "calories": round(updated_meal.nutrition.calories, 1),
            "protein": round(updated_meal.nutrition.protein, 1),
            "carbs": round(updated_meal.nutrition.carbs, 1),
            "fat": round(updated_meal.nutrition.fat, 1)
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


@handles(AnalyzeMealImageCommand)
class AnalyzeMealImageCommandHandler(EventHandler[AnalyzeMealImageCommand, Dict[str, Any]]):
    """Handler for analyzing meal images."""
    
    def __init__(
        self,
        meal_repository: MealRepositoryPort = None,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None
    ):
        self.meal_repository = meal_repository
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.vision_service = kwargs.get('vision_service', self.vision_service)
        self.gpt_parser = kwargs.get('gpt_parser', self.gpt_parser)
    
    async def handle(self, command: AnalyzeMealImageCommand) -> Dict[str, Any]:
        """Analyze meal image using AI vision service."""
        if not all([self.meal_repository, self.vision_service, self.gpt_parser]):
            raise RuntimeError("Required dependencies not configured")
        
        # Get meal
        meal = self.meal_repository.find_by_id(command.meal_id)
        if not meal:
            raise ResourceNotFoundException(f"Meal with ID {command.meal_id} not found")
        
        if not meal.image:
            raise ValidationException(f"Meal {command.meal_id} has no image to analyze")
        
        try:
            # Update status to analyzing
            meal.status = MealStatus.ANALYZING
            self.meal_repository.save(meal)
            
            # Get image store to load the image bytes
            from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
            image_store = CloudinaryImageStore()
            
            # Load image bytes
            image_bytes = image_store.load(meal.image.image_id)
            if not image_bytes:
                raise RuntimeError(f"Could not load image {meal.image.image_id}")
            
            # Perform AI analysis
            logger.info(f"Performing AI vision analysis for meal {command.meal_id}")
            vision_result = self.vision_service.analyze(image_bytes)
            
            # Parse the response
            nutrition = self.gpt_parser.parse_to_nutrition(vision_result)
            dish_name = self.gpt_parser.parse_dish_name(vision_result)
            
            # Update meal with analysis results
            meal.dish_name = dish_name or "Unknown dish"
            meal.status = MealStatus.READY
            meal.ready_at = datetime.now()
            meal.raw_gpt_json = self.gpt_parser.extract_raw_json(vision_result)
            
            # Use the parsed nutrition directly
            meal.nutrition = nutrition
            
            # Save the analyzed meal
            self.meal_repository.save(meal)
            
            logger.info(f"Meal {command.meal_id} analysis completed successfully")
            
            return {
                "meal_id": command.meal_id,
                "status": "ready",
                "dish_name": meal.dish_name,
                "nutrition": {
                    "calories": meal.nutrition.calories,
                    "protein": meal.nutrition.protein,
                    "carbs": meal.nutrition.carbs,
                    "fat": meal.nutrition.fat,
                    "fiber": meal.nutrition.fiber if hasattr(meal.nutrition, 'fiber') else 0
                },
                "events": [
                    MealAnalysisStartedEvent(
                        aggregate_id=command.meal_id,
                        meal_id=command.meal_id,
                        analysis_type="vision_ai"
                    )
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze meal {command.meal_id}: {str(e)}")
            # Update meal status to failed
            meal.status = MealStatus.FAILED
            meal.error_message = str(e)
            self.meal_repository.save(meal)
            raise