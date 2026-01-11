"""
Handler for immediate meal image upload and analysis.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from src.app.commands.meal import UploadMealImageImmediatelyCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal import MealImage
from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.infra.cache.cache_service import CacheService
from src.domain.services.timezone_utils import utc_now

logger = logging.getLogger(__name__)


@handles(UploadMealImageImmediatelyCommand)
class UploadMealImageImmediatelyHandler(EventHandler[UploadMealImageImmediatelyCommand, Meal]):
    """Handler for immediate meal image upload and analysis."""
    
    def __init__(
        self,
        image_store: ImageStorePort = None,
        meal_repository: MealRepositoryPort = None,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None,
        cache_service: Optional[CacheService] = None,
    ):
        self.image_store = image_store
        self.meal_repository = meal_repository
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
        self.cache_service = cache_service
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.image_store = kwargs.get('image_store', self.image_store)
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.vision_service = kwargs.get('vision_service', self.vision_service)
        self.gpt_parser = kwargs.get('gpt_parser', self.gpt_parser)
        self.cache_service = kwargs.get('cache_service', self.cache_service)
    
    async def handle(self, command: UploadMealImageImmediatelyCommand) -> Meal:
        """Handle immediate meal image upload and analysis."""
        if not all([self.image_store, self.meal_repository, self.vision_service, self.gpt_parser]):
            raise RuntimeError("Required dependencies not configured")
        
        try:
            # Upload image to storage
            logger.info("Uploading image to storage")
            image_url = self.image_store.save(
                command.file_contents,
                command.content_type
            )

            image_id = image_url
            if image_url.startswith("mock://images/"):
                image_id = image_url.replace("mock://images/", "")
            elif "cloudinary.com" in image_url:
                # Extract public_id from cloudinary URL
                parts = image_url.split("/")
                if len(parts) > 1:
                    # Get the last part and remove file extension
                    image_id = parts[-1].split(".")[0]
            
            # Determine the meal date - use target_date if provided, otherwise use now
            meal_date = command.target_date if command.target_date else utc_now().date()
            meal_datetime = datetime.combine(meal_date, utc_now().time())
            
            logger.info(f"Creating meal record for date: {meal_date}")
            
            # Create meal record with ANALYZING status
            meal = Meal(
                meal_id=str(uuid4()),
                user_id=command.user_id,
                status=MealStatus.ANALYZING,
                created_at=meal_datetime,
                image=MealImage(
                    image_id=image_id,
                    format="jpeg" if "jpeg" in command.content_type else "png",
                    size_bytes=len(command.file_contents),
                    url=image_url
                )
            )
            
            # Save initial meal record
            saved_meal = self.meal_repository.save(meal)
            logger.info(f"Created meal record {saved_meal.meal_id} with ANALYZING status")
            
            # Perform AI analysis immediately
            logger.info(f"Performing AI vision analysis for meal {saved_meal.meal_id}")
            vision_result = self.vision_service.analyze(command.file_contents)
            
            # Parse the response
            nutrition = self.gpt_parser.parse_to_nutrition(vision_result)
            dish_name = self.gpt_parser.parse_dish_name(vision_result)
            
            # Update meal with analysis results
            meal.dish_name = dish_name or "Unknown dish"
            meal.status = MealStatus.READY
            meal.ready_at = utc_now()
            meal.raw_gpt_json = self.gpt_parser.extract_raw_json(vision_result)
            
            # Use the parsed nutrition directly
            meal.nutrition = nutrition
            
            # Save the fully analyzed meal
            final_meal = self.meal_repository.save(meal)
            logger.info(f"Meal {final_meal.meal_id} analysis completed successfully with status {final_meal.status}")
            await self._invalidate_daily_macros(command.user_id, meal_date)
            
            return final_meal
            
        except Exception as e:
            logger.error(f"Failed to upload and analyze meal immediately: {str(e)}")
            # If meal was created, update it to failed status
            if 'meal' in locals() and meal.meal_id:
                meal.status = MealStatus.FAILED
                meal.error_message = str(e)
                self.meal_repository.save(meal)
            raise

    async def _invalidate_daily_macros(self, user_id, target_date):
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.daily_macros(user_id, target_date)
        await self.cache_service.invalidate(cache_key)