"""
Handler for immediate meal image upload and analysis.
"""
import asyncio
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
from src.domain.services.meal_analysis.fast_path_policy import MealAnalyzeFastPathPolicy
from src.domain.services.meal_analysis.deepl_meal_translation_service import DeepLMealTranslationService
from src.domain.services.meal_type_determination_service import determine_meal_type_from_timestamp
from src.domain.utils.timezone_utils import utc_now, get_zone_info, is_valid_timezone, noon_utc_for_date
from src.infra.repositories.meal_repository import MealProjection
from src.infra.config.settings import get_settings

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
        meal_translation_service: Optional[DeepLMealTranslationService] = None,
        fast_path_policy: Optional[MealAnalyzeFastPathPolicy] = None,
    ):
        self.uow = uow
        self.event_bus = event_bus
        self.image_store = image_store
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
        self.meal_translation_service = meal_translation_service
        if fast_path_policy is None:
            self._fast_path_policy = MealAnalyzeFastPathPolicy.from_settings(get_settings())
        else:
            self._fast_path_policy = fast_path_policy

    def _run_vision_analysis(
        self, command: UploadMealImageImmediatelyCommand, meal_id: str
    ) -> Any:
        max_attempts = max(1, self._fast_path_policy.max_attempts)
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                if command.user_description:
                    from src.domain.strategies.meal_analysis_strategy import AnalysisStrategyFactory
                    logger.info(
                        f"[PHASE-1-START] meal={meal_id} | "
                        f"vision analysis with user context | "
                        f"attempt={attempt}/{max_attempts}"
                    )
                    strategy = AnalysisStrategyFactory.create_user_context_strategy(command.user_description)
                    return self.vision_service.analyze_with_strategy(command.file_contents, strategy)

                logger.info(
                    f"[PHASE-1-START] meal={meal_id} | "
                    f"vision analysis | attempt={attempt}/{max_attempts}"
                )
                return self.vision_service.analyze(command.file_contents)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"[PHASE-1-RETRY] meal={meal_id} | "
                    f"attempt={attempt}/{max_attempts} failed: {e}"
                )
                if attempt == max_attempts:
                    raise

        if last_error:
            raise last_error
        raise RuntimeError("Vision analysis failed without a captured exception.")

    def _run_vision_once(self, command: UploadMealImageImmediatelyCommand, meal_id: str) -> Any:
        """Single-attempt vision call used by the parallel path (no retries to preserve latency budget)."""
        if command.user_description:
            from src.domain.strategies.meal_analysis_strategy import AnalysisStrategyFactory
            strategy = AnalysisStrategyFactory.create_user_context_strategy(command.user_description)
            return self.vision_service.analyze_with_strategy(command.file_contents, strategy)
        return self.vision_service.analyze(command.file_contents)

    async def _handle_parallel_upload(
        self,
        command: UploadMealImageImmediatelyCommand,
    ) -> Meal:
        """Run image upload and AI analysis concurrently then apply failure matrix."""
        async with self.uow as uow:
            user_timezone = await uow.users.get_user_timezone(command.user_id)
            if not user_timezone or not is_valid_timezone(user_timezone):
                user_timezone = "UTC"

            now = utc_now()
            meal_date = command.target_date if command.target_date else now.date()
            if command.target_date and command.target_date != now.date():
                meal_datetime = noon_utc_for_date(meal_date, user_timezone)
            else:
                meal_datetime = now

            zone_info = get_zone_info(user_timezone)
            local_datetime = meal_datetime.astimezone(zone_info)
            meal_type = determine_meal_type_from_timestamp(local_datetime)

            placeholder_image_id = str(uuid4())
            meal = Meal(
                meal_id=str(uuid4()),
                user_id=command.user_id,
                status=MealStatus.ANALYZING,
                created_at=meal_datetime,
                meal_type=meal_type,
                image=MealImage(
                    image_id=placeholder_image_id,
                    format="jpeg" if "jpeg" in command.content_type else "png",
                    size_bytes=len(command.file_contents),
                ),
                source="scanner",
            )
            saved_meal = await uow.meals.save(meal)
            await uow.commit()
            logger.info(f"[PARALLEL] Created meal {saved_meal.meal_id} with ANALYZING status")

        logger.info(f"[PHASE-UPLOAD-START] meal={saved_meal.meal_id}")
        logger.info(f"[PHASE-ANALYSIS-START] meal={saved_meal.meal_id}")

        loop = asyncio.get_event_loop()
        start = time.time()
        upload_task = loop.run_in_executor(
            None, self.image_store.save, command.file_contents, command.content_type, placeholder_image_id
        )
        analysis_task = loop.run_in_executor(
            None, self._run_vision_once, command, saved_meal.meal_id
        )
        results = await asyncio.gather(upload_task, analysis_task, return_exceptions=True)
        total_elapsed = time.time() - start

        upload_result, analysis_result = results
        upload_error = upload_result if isinstance(upload_result, Exception) else None
        analysis_error = analysis_result if isinstance(analysis_result, Exception) else None

        if upload_error:
            logger.warning(f"[PHASE-UPLOAD-FAIL] meal={saved_meal.meal_id} | error={upload_error}")
        else:
            logger.info(f"[PHASE-UPLOAD-COMPLETE] meal={saved_meal.meal_id} | elapsed={total_elapsed:.2f}s")

        if analysis_error:
            logger.warning(f"[PHASE-ANALYSIS-FAIL] meal={saved_meal.meal_id} | error={analysis_error}")
        else:
            logger.info(f"[PHASE-ANALYSIS-COMPLETE] meal={saved_meal.meal_id} | elapsed={total_elapsed:.2f}s")

        if upload_error or analysis_error:
            meal.status = MealStatus.FAILED
            # Prioritise analysis error (non-food domain) over upload error
            error_to_raise = analysis_error or upload_error
            meal.error_message = str(error_to_raise)
            async with self.uow as uow:
                await uow.meals.save(meal)
                await uow.commit()
            raise error_to_raise

        # Both succeeded — populate image URL and nutrition
        image_url = upload_result
        meal.image = MealImage(
            image_id=placeholder_image_id,
            format="jpeg" if "jpeg" in command.content_type else "png",
            size_bytes=len(command.file_contents),
            url=image_url,
        )

        nutrition = self.gpt_parser.parse_to_nutrition(analysis_result)
        dish_name = self.gpt_parser.parse_dish_name(analysis_result)

        has_food = (
            nutrition
            and nutrition.food_items
            and len(nutrition.food_items) > 0
            and nutrition.calories > 0
        )
        if not has_food:
            meal.status = MealStatus.FAILED
            meal.error_message = "No edible food detected"
            async with self.uow as uow:
                await uow.meals.save(meal)
                await uow.commit()
            raise ValueError(
                "No edible food detected in the image. "
                "Please take a photo of food and try again."
            )

        meal.dish_name = dish_name or "Unknown dish"
        meal.emoji = self.gpt_parser.parse_emoji(analysis_result)
        meal.status = MealStatus.READY
        meal.ready_at = utc_now()
        meal.raw_gpt_json = self.gpt_parser.extract_raw_json(analysis_result)
        meal.nutrition = nutrition

        # Translation for non-English languages
        if (
            command.language
            and command.language != "en"
            and self.meal_translation_service
            and nutrition
            and nutrition.food_items
        ):
            try:
                await self.meal_translation_service.translate_meal(
                    meal=meal,
                    dish_name=meal.dish_name,
                    food_items=nutrition.food_items,
                    target_language=command.language,
                )
                logger.info(f"[TRANSLATION] meal={meal.meal_id} translated to {command.language}")
            except Exception as e:
                logger.warning(f"[TRANSLATION] failed for meal={meal.meal_id}: {e}")

        async with self.uow as uow:
            final_meal = await uow.meals.save(meal)
            await uow.commit()
            logger.info(
                f"[ANALYSIS-COMPLETE] meal={final_meal.meal_id} | "
                f"total_elapsed={total_elapsed:.2f}s | status={final_meal.status}"
            )
            final_meal = await uow.meals.find_by_id(
                meal.meal_id, projection=MealProjection.FULL_WITH_TRANSLATIONS
            )

        await self.event_bus.publish(MealCacheInvalidationRequiredEvent(
            aggregate_id=command.user_id,
            user_id=command.user_id,
            meal_date=meal_date,
        ))

        return final_meal

    async def handle(self, command: UploadMealImageImmediatelyCommand) -> Meal:
        """Handle immediate meal image upload and analysis."""
        if not all([self.image_store, self.vision_service, self.gpt_parser]):
            raise RuntimeError("Required dependencies not configured")

        return await self._handle_parallel_upload(command)
