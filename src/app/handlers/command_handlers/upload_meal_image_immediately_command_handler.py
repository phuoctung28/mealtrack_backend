"""
Handler for immediate meal image upload and analysis.
"""
import logging
import time
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
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.meal_suggestion.translation_service import TranslationService
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(UploadMealImageImmediatelyCommand)
class UploadMealImageImmediatelyHandler(EventHandler[UploadMealImageImmediatelyCommand, Meal]):
    """Handler for immediate meal image upload and analysis."""

    def __init__(
        self,
        image_store: ImageStorePort = None,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None,
        cache_service: Optional[CacheService] = None,
        translation_service: Optional[TranslationService] = None,
    ):
        self.image_store = image_store
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
        self.cache_service = cache_service
        self.translation_service = translation_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.image_store = kwargs.get('image_store', self.image_store)
        self.vision_service = kwargs.get('vision_service', self.vision_service)
        self.gpt_parser = kwargs.get('gpt_parser', self.gpt_parser)
        self.cache_service = kwargs.get('cache_service', self.cache_service)
        self.translation_service = kwargs.get('translation_service', self.translation_service)
    
    async def handle(self, command: UploadMealImageImmediatelyCommand) -> Meal:
        """Handle immediate meal image upload and analysis."""
        if not all([self.image_store, self.vision_service, self.gpt_parser]):
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
            
            # Save initial meal record using UoW
            with UnitOfWork() as uow:
                saved_meal = uow.meals.save(meal)
                uow.commit()
                logger.info(f"Created meal record {saved_meal.meal_id} with ANALYZING status")

            # PHASE 1: AI Vision Analysis (generates content in English)
            phase1_start = time.time()
            if command.user_description:
                from src.domain.strategies.meal_analysis_strategy import AnalysisStrategyFactory
                logger.info(
                    f"[PHASE-1-START] meal={saved_meal.meal_id} | "
                    f"vision analysis with user context"
                )
                strategy = AnalysisStrategyFactory.create_user_context_strategy(command.user_description)
                vision_result = self.vision_service.analyze_with_strategy(command.file_contents, strategy)
            else:
                logger.info(
                    f"[PHASE-1-START] meal={saved_meal.meal_id} | "
                    f"vision analysis"
                )
                vision_result = self.vision_service.analyze(command.file_contents)
            phase1_elapsed = time.time() - phase1_start
            logger.info(
                f"[PHASE-1-COMPLETE] meal={saved_meal.meal_id} | "
                f"elapsed={phase1_elapsed:.2f}s"
            )

            # PHASE 2: Translation (if non-English)
            phase2_elapsed = 0.0
            if command.language and command.language != "en" and self.translation_service:
                phase2_start = time.time()
                logger.info(
                    f"[PHASE-2-START] meal={saved_meal.meal_id} | "
                    f"translating to {command.language}"
                )
                # Translation logic would go here when implemented
                # vision_result = self.translation_service.translate(vision_result, command.language)
                phase2_elapsed = time.time() - phase2_start
                logger.info(
                    f"[PHASE-2-COMPLETE] meal={saved_meal.meal_id} | "
                    f"elapsed={phase2_elapsed:.2f}s | "
                    f"language={command.language}"
                )

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

            # Save the fully analyzed meal using UoW
            with UnitOfWork() as uow:
                final_meal = uow.meals.save(meal)
                uow.commit()
                total_elapsed = phase1_elapsed + phase2_elapsed
                logger.info(
                    f"[ANALYSIS-COMPLETE] meal={final_meal.meal_id} | "
                    f"total_elapsed={total_elapsed:.2f}s | "
                    f"phase1={phase1_elapsed:.2f}s | "
                    f"phase2={phase2_elapsed:.2f}s | "
                    f"language={command.language} | "
                    f"status={final_meal.status}"
                )
            
            await self._invalidate_daily_macros(command.user_id, meal_date)

            return final_meal
            
        except Exception as e:
            logger.error(f"Failed to upload and analyze meal immediately: {str(e)}")
            # If meal was created, update it to failed status
            if 'meal' in locals() and meal.meal_id:
                meal.status = MealStatus.FAILED
                meal.error_message = str(e)
                with UnitOfWork() as uow:
                    uow.meals.save(meal)
                    uow.commit()
            raise

    async def _invalidate_daily_macros(self, user_id, target_date):
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.daily_macros(user_id, target_date)
        await self.cache_service.invalidate(cache_key)
