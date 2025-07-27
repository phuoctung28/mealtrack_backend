"""
Event handler for meal analysis events.
"""
import logging
from datetime import datetime

from src.app.events.meal import MealImageUploadedEvent
from src.domain.model.meal import MealStatus
from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
from src.infra.adapters.vision_ai_service import VisionAIService
from src.infra.repositories.meal_repository import MealRepository

logger = logging.getLogger(__name__)


class MealAnalysisEventHandler:
    """Handler for meal analysis events."""
    
    def __init__(
        self,
        meal_repository: MealRepositoryPort = None,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None,
        image_store: ImageStorePort = None
    ):
        self.meal_repository = meal_repository or MealRepository()
        self.vision_service = vision_service or VisionAIService()
        self.gpt_parser = gpt_parser or GPTResponseParser()
        self.image_store = image_store or CloudinaryImageStore()
    
    async def handle_meal_image_uploaded(self, event: MealImageUploadedEvent) -> None:
        """Handle meal image uploaded event by triggering background analysis."""
        logger.info(f"EVENT HANDLER CALLED: Received MealImageUploadedEvent for meal {event.meal_id}")
        try:
            logger.info(f"Starting background analysis for meal {event.meal_id}")
            
            # Get the meal from repository
            meal = self.meal_repository.find_by_id(event.meal_id)
            if not meal:
                logger.error(f"Meal {event.meal_id} not found for background analysis")
                return
            
            # Skip if already processed
            if meal.status != MealStatus.PROCESSING:
                logger.info(f"Meal {event.meal_id} already processed with status {meal.status}")
                return
            
            # Update status to ANALYZING
            meal.status = MealStatus.ANALYZING
            self.meal_repository.save(meal)
            logger.info(f"Updated meal {event.meal_id} status to ANALYZING")
            
            # Try to perform real analysis if we can get image contents
            # Otherwise fall back to mock analysis
            await self._perform_analysis(meal)
            
        except Exception as e:
            logger.error(f"Error processing meal image upload event for meal {event.meal_id}: {str(e)}")
            await self._mark_meal_as_failed(event.meal_id, str(e))
    
    async def _perform_analysis(self, meal):
        """Perform real AI analysis using the same logic as UploadMealImageImmediatelyHandler."""
        try:
            # Add small delay to simulate processing time
            import asyncio
            await asyncio.sleep(1)
            
            # Get image contents from the image store
            logger.info(f"Loading image contents for meal {meal.meal_id}")
            image_contents = self.image_store.load(meal.image.image_id)
            
            if not image_contents:
                raise Exception(f"Could not load image contents for image_id: {meal.image.image_id}")
            
            logger.info(f"Performing real AI analysis for meal {meal.meal_id}")
            
            # Perform AI analysis (same as UploadMealImageImmediatelyHandler)
            vision_result = self.vision_service.analyze(image_contents)
            
            # Parse the response (same as UploadMealImageImmediatelyHandler)
            nutrition = self.gpt_parser.parse_to_nutrition(vision_result)
            dish_name = self.gpt_parser.parse_dish_name(vision_result)
            
            # Update meal with analysis results (same as UploadMealImageImmediatelyHandler)
            meal.dish_name = dish_name or "Unknown dish"
            meal.status = MealStatus.READY
            meal.ready_at = datetime.now()
            meal.raw_gpt_json = self.gpt_parser.extract_raw_json(vision_result)
            
            # Use the parsed nutrition directly (same as UploadMealImageImmediatelyHandler)
            meal.nutrition = nutrition
            
            # Save the fully analyzed meal
            self.meal_repository.save(meal)
            logger.info(f"Real analysis completed for meal {meal.meal_id}")
            
        except Exception as e:
            logger.error(f"Analysis failed for meal {meal.meal_id}: {str(e)}")
            await self._mark_meal_as_failed(meal.meal_id, str(e))
    
    async def _mark_meal_as_failed(self, meal_id: str, error_message: str):
        """Mark a meal as failed with error message."""
        try:
            meal = self.meal_repository.find_by_id(meal_id)
            if meal:
                meal.status = MealStatus.FAILED
                meal.error_message = error_message
                self.meal_repository.save(meal)
                logger.info(f"Marked meal {meal_id} as failed")
        except Exception as save_error:
            logger.error(f"Failed to update meal status to failed: {str(save_error)}")

