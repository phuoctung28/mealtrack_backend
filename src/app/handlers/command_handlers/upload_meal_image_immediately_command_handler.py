"""
Handler for immediate meal image upload and analysis.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from src.app.commands.meal import UploadMealImageImmediatelyCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal.meal_cache_invalidation_required_event import MealCacheInvalidationRequiredEvent
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal import MealImage
from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.meal_analysis.translation_service import MealAnalysisTranslationService
from src.domain.services.meal_type_determination_service import determine_meal_type_from_timestamp
from src.domain.utils.timezone_utils import utc_now, get_zone_info, is_valid_timezone, noon_utc_for_date
from src.infra.repositories.meal_repository import MealProjection

logger = logging.getLogger(__name__)


@handles(UploadMealImageImmediatelyCommand)
class UploadMealImageImmediatelyHandler(EventHandler[UploadMealImageImmediatelyCommand, Meal]):
    """Handler for immediate meal image upload and analysis."""

    def __init__(
        self,
        uow: UnitOfWorkPort,
        event_bus: Any,
        image_store: ImageStorePort = None,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None,
        meal_translation_service: Optional[MealAnalysisTranslationService] = None,
    ):
        self.uow = uow
        self.event_bus = event_bus
        self.image_store = image_store
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
        self.meal_translation_service = meal_translation_service
    
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
            
            # ---- MERGED UoW 1+2: get timezone + create initial meal record ----
            async with self.uow as uow:
                user_timezone = await uow.users.get_user_timezone(command.user_id)

                # Fallback to UTC if not set
                if not user_timezone or not is_valid_timezone(user_timezone):
                    user_timezone = "UTC"
                    logger.info("Using UTC fallback for meal type detection")

                # Determine the meal date and datetime
                now = utc_now()
                meal_date = command.target_date if command.target_date else now.date()
                if command.target_date and command.target_date != now.date():
                    meal_datetime = noon_utc_for_date(meal_date, user_timezone)
                else:
                    meal_datetime = now

                logger.info(f"Creating meal record for date: {meal_date}")

                zone_info = get_zone_info(user_timezone)
                local_datetime = meal_datetime.astimezone(zone_info)
                logger.info(
                    f"Meal type detection: UTC={meal_datetime.isoformat()} → "
                    f"Local={local_datetime.isoformat()} (timezone={user_timezone})"
                )

                meal_type = determine_meal_type_from_timestamp(local_datetime)

                meal = Meal(
                    meal_id=str(uuid4()),
                    user_id=command.user_id,
                    status=MealStatus.ANALYZING,
                    created_at=meal_datetime,
                    meal_type=meal_type,
                    image=MealImage(
                        image_id=image_id,
                        format="jpeg" if "jpeg" in command.content_type else "png",
                        size_bytes=len(command.file_contents),
                        url=image_url,
                    ),
                    source="scanner",
                )

                saved_meal = await uow.meals.save(meal)
                await uow.commit()
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
            # Note: Translation placeholder - original code removed, translation now
            # integrated after parsing below

            # Parse the response
            nutrition = self.gpt_parser.parse_to_nutrition(vision_result)
            dish_name = self.gpt_parser.parse_dish_name(vision_result)

            # Validate: reject if no edible food detected
            has_food = (
                nutrition
                and nutrition.food_items
                and len(nutrition.food_items) > 0
                and nutrition.calories > 0
            )
            if not has_food:
                raise ValueError(
                    "No edible food detected in the image. "
                    "Please take a photo of food and try again."
                )

            # Update meal with analysis results
            meal.dish_name = dish_name or "Unknown dish"
            meal.emoji = self.gpt_parser.parse_emoji(vision_result)
            meal.status = MealStatus.READY
            meal.ready_at = utc_now()
            meal.raw_gpt_json = self.gpt_parser.extract_raw_json(vision_result)
            meal.nutrition = nutrition

            # PHASE 2: Translation (after parsing, before final save)
            phase2_elapsed = 0.0
            if command.language and command.language != "en" and self.meal_translation_service:
                phase2_start = time.time()
                logger.info(
                    f"[PHASE-2-START] meal={saved_meal.meal_id} | "
                    f"translating to {command.language}"
                )
                if nutrition and nutrition.food_items:
                    try:
                        translation = await self.meal_translation_service.translate_meal(
                            meal=saved_meal,
                            dish_name=meal.dish_name,
                            food_items=nutrition.food_items,
                            target_language=command.language
                        )
                        if translation:
                            logger.info(
                                f"[PHASE-2] translation saved for meal={saved_meal.meal_id}, "
                                f"language={command.language}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"[PHASE-2] translation failed for meal={saved_meal.meal_id}: {e}"
                        )
                        # Don't fail the whole analysis if translation fails
                phase2_elapsed = time.time() - phase2_start
                logger.info(
                    f"[PHASE-2-COMPLETE] meal={saved_meal.meal_id} | "
                    f"elapsed={phase2_elapsed:.2f}s | "
                    f"language={command.language}"
                )

            # ---- MERGED UoW 3+4: save final meal + reload with translations ----
            async with self.uow as uow:
                final_meal = await uow.meals.save(meal)
                await uow.commit()
                total_elapsed = phase1_elapsed + phase2_elapsed
                logger.info(
                    f"[ANALYSIS-COMPLETE] meal={final_meal.meal_id} | "
                    f"total_elapsed={total_elapsed:.2f}s | "
                    f"phase1={phase1_elapsed:.2f}s | "
                    f"phase2={phase2_elapsed:.2f}s | "
                    f"language={command.language} | "
                    f"status={final_meal.status}"
                )
                final_meal = await uow.meals.find_by_id(meal.meal_id, projection=MealProjection.FULL_WITH_TRANSLATIONS)

            await self.event_bus.publish(MealCacheInvalidationRequiredEvent(
                aggregate_id=command.user_id,
                user_id=command.user_id,
                meal_date=meal_date,
            ))

            return final_meal

        except Exception as e:
            logger.error(f"Failed to upload and analyze meal immediately: {str(e)}")
            # If meal was created, update it to failed status
            if 'meal' in locals() and meal.meal_id:
                meal.status = MealStatus.FAILED
                meal.error_message = str(e)
                async with self.uow as uow:
                    await uow.meals.save(meal)
                    await uow.commit()
            raise
