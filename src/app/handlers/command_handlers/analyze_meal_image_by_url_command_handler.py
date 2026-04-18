"""
Handler for immediate meal image analysis using pre-uploaded image URL.
"""
import logging
import time
from typing import Any, Optional
from uuid import uuid4

from src.app.commands.meal import AnalyzeMealImageByUrlCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal.meal_cache_invalidation_required_event import MealCacheInvalidationRequiredEvent
from src.domain.model.meal import Meal, MealStatus, MealImage
from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.meal_analysis.translation_service import (
    MealAnalysisTranslationService,
)
from src.domain.services.meal_type_determination_service import (
    determine_meal_type_from_timestamp,
)
from src.domain.utils.timezone_utils import (
    get_zone_info,
    is_valid_timezone,
    noon_utc_for_date,
    utc_now,
)
from src.infra.repositories.meal_repository import MealProjection

logger = logging.getLogger(__name__)


@handles(AnalyzeMealImageByUrlCommand)
class AnalyzeMealImageByUrlHandler(
    EventHandler[AnalyzeMealImageByUrlCommand, Meal]
):
    """Handler for immediate meal image analysis from URL."""

    def __init__(
        self,
        uow: UnitOfWorkPort,
        event_bus: Any,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None,
        meal_translation_service: Optional[MealAnalysisTranslationService] = None,
    ):
        self.uow = uow
        self.event_bus = event_bus
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
        self.meal_translation_service = meal_translation_service

    async def handle(self, command: AnalyzeMealImageByUrlCommand) -> Meal:
        """Handle immediate meal image analysis from Cloudinary URL."""
        if not all([self.vision_service, self.gpt_parser]):
            raise RuntimeError("Required dependencies not configured")

        try:
            image_id = command.public_id.split("/")[-1]

            with self.uow as uow:
                user_timezone = uow.users.get_user_timezone(command.user_id)

            if not user_timezone or not is_valid_timezone(user_timezone):
                user_timezone = "UTC"
                logger.info("Using UTC fallback for meal type detection")

            now = utc_now()
            meal_date = command.target_date if command.target_date else now.date()
            if command.target_date and command.target_date != now.date():
                # Past/future date — use noon to avoid date-boundary issues
                meal_datetime = noon_utc_for_date(meal_date, user_timezone)
                logger.info(f"Using noon for past/future date: {meal_datetime}")
            else:
                # Today or no date — use actual current time
                meal_datetime = now
                logger.info(f"Using current time: {meal_datetime}")

            zone_info = get_zone_info(user_timezone)
            local_datetime = meal_datetime.astimezone(zone_info)
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
                    size_bytes=command.file_size_bytes,
                    url=command.image_url,
                ),
                source="scanner",
            )

            with self.uow as uow:
                saved_meal = uow.meals.save(meal)
                uow.commit()

            phase1_start = time.time()
            if command.user_description:
                from src.domain.strategies.meal_analysis_strategy import (
                    AnalysisStrategyFactory,
                )

                strategy = AnalysisStrategyFactory.create_user_context_strategy(
                    command.user_description
                )
                vision_result = self.vision_service.analyze_by_url_with_strategy(
                    command.image_url, strategy
                )
            else:
                vision_result = self.vision_service.analyze_by_url(command.image_url)
            phase1_elapsed = time.time() - phase1_start

            nutrition = self.gpt_parser.parse_to_nutrition(vision_result)
            dish_name = self.gpt_parser.parse_dish_name(vision_result)

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

            meal = meal.mark_ready(
                nutrition=nutrition,
                dish_name=dish_name or "Unknown dish",
                raw_gpt_json=self.gpt_parser.extract_raw_json(vision_result),
                emoji=self.gpt_parser.parse_emoji(vision_result),
            )

            phase2_elapsed = 0.0
            if (
                command.language
                and command.language != "en"
                and self.meal_translation_service
            ):
                phase2_start = time.time()
                if nutrition and nutrition.food_items:
                    try:
                        await self.meal_translation_service.translate_meal(
                            meal=saved_meal,
                            dish_name=meal.dish_name,
                            food_items=nutrition.food_items,
                            target_language=command.language,
                        )
                    except Exception as e:
                        logger.warning(
                            "Translation failed for meal=%s: %s",
                            saved_meal.meal_id,
                            e,
                        )
                phase2_elapsed = time.time() - phase2_start

            with self.uow as uow:
                final_meal = uow.meals.save(meal)
                uow.commit()
                logger.info(
                    "[ANALYSIS-COMPLETE] meal=%s | total_elapsed=%.2fs | phase1=%.2fs | phase2=%.2fs | language=%s | status=%s",
                    final_meal.meal_id,
                    phase1_elapsed + phase2_elapsed,
                    phase1_elapsed,
                    phase2_elapsed,
                    command.language,
                    final_meal.status,
                )

            with self.uow as uow:
                final_meal = uow.meals.find_by_id(meal.meal_id, projection=MealProjection.FULL_WITH_TRANSLATIONS)

            await self.event_bus.publish(MealCacheInvalidationRequiredEvent(
                aggregate_id=command.user_id,
                user_id=command.user_id,
                meal_date=meal_date,
            ))
            return final_meal
        except Exception as e:
            logger.error("Failed to analyze meal by URL: %s", str(e))
            if "meal" in locals() and meal.meal_id:
                meal = meal.mark_failed(error_message=str(e))
                with self.uow as uow:
                    uow.meals.save(meal)
                    uow.commit()
            raise
