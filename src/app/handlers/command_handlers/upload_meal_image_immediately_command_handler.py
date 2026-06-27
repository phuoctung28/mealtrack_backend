"""
Handler for immediate meal image upload and analysis.
"""

import logging
import time
from typing import Any
from uuid import uuid4

from src.app.commands.meal import UploadMealImageImmediatelyCommand
from src.app.events.base import EventHandler, handles
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.domain.exceptions.ai_exceptions import AIVisionError, AIVisionFailureKind
from src.domain.model.meal import Meal, MealImage, MealStatus
from src.domain.model.meal_projection import MealProjection
from src.domain.parsers.vision_response_parser import (
    VisionResponseParser as GPTResponseParser,
)
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.meal_analysis.deepl_meal_translation_service import (
    DeepLMealTranslationService,
)
from src.domain.services.meal_analysis.fast_path_policy import MealAnalyzeFastPathPolicy
from src.domain.services.meal_type_determination_service import (
    determine_meal_type_from_timestamp,
)
from src.domain.utils.timezone_utils import (
    get_zone_info,
    is_valid_timezone,
    noon_utc_for_date,
    utc_now,
)
from src.infra.config.settings import get_settings
from src.observability import capture_message, distribution_metric, increment_metric

logger = logging.getLogger(__name__)


@handles(UploadMealImageImmediatelyCommand)
class UploadMealImageImmediatelyHandler(
    EventHandler[UploadMealImageImmediatelyCommand, Meal]
):
    """Handler for immediate meal image upload and analysis."""

    def __init__(
        self,
        uow: AsyncUnitOfWorkPort,
        event_bus: Any,
        image_store: ImageStorePort = None,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None,
        meal_translation_service: DeepLMealTranslationService | None = None,
        fast_path_policy: MealAnalyzeFastPathPolicy | None = None,
        cache_invalidation: CacheInvalidationService | None = None,
    ):
        self.uow = uow
        self.event_bus = event_bus
        self.cache_invalidation = cache_invalidation
        self.image_store = image_store
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
        self.meal_translation_service = meal_translation_service
        if fast_path_policy is None:
            self._fast_path_policy = MealAnalyzeFastPathPolicy.from_settings(
                get_settings()
            )
        else:
            self._fast_path_policy = fast_path_policy

    async def _run_vision_analysis(
        self, command: UploadMealImageImmediatelyCommand, meal_id: str
    ) -> Any:
        max_attempts = max(1, self._fast_path_policy.max_attempts)
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                if command.user_description:
                    from src.domain.strategies.meal_analysis_strategy import (
                        AnalysisStrategyFactory,
                    )

                    logger.info(
                        f"[PHASE-1-START] meal={meal_id} | "
                        f"vision analysis with user context | "
                        f"attempt={attempt}/{max_attempts}"
                    )
                    strategy = AnalysisStrategyFactory.create_user_context_strategy(
                        command.user_description
                    )
                    return await self.vision_service.analyze_with_strategy(
                        command.file_contents, strategy
                    )

                logger.info(
                    f"[PHASE-1-START] meal={meal_id} | "
                    f"vision analysis | attempt={attempt}/{max_attempts}"
                )
                return await self.vision_service.analyze(command.file_contents)
            except Exception as e:
                last_error = e
                # Deterministic failures (schema/parse/no-food) cannot be fixed by retrying
                # the same provider chain — skip outer retry and surface immediately
                if isinstance(e, AIVisionError) and e.kind in (
                    AIVisionFailureKind.schema_validation,
                    AIVisionFailureKind.json_parse,
                    AIVisionFailureKind.no_food,
                ):
                    logger.warning(
                        "[PHASE-1-NO-RETRY] meal=%s kind=%s attempt=%d/%d",
                        meal_id, e.kind.value, attempt, max_attempts,
                    )
                    raise
                logger.warning(
                    f"[PHASE-1-RETRY] meal={meal_id} | "
                    f"attempt={attempt}/{max_attempts} failed: {e}"
                )
                if attempt == max_attempts:
                    raise

        if last_error:
            raise last_error
        raise RuntimeError("Vision analysis failed without a captured exception.")

    def _validate_cloudinary_url(self, url: str) -> bool:
        """Validate that the Cloudinary response is a valid HTTPS URL."""
        return url is not None and url.startswith("https://")

    def _capture_rejected_scan(
        self,
        *,
        image_id: str,
        image_url: str,
        reason: str,
    ) -> None:
        capture_message(
            "meal_scan.image_rejected",
            level="warning",
            context={
                "component": "meal_scan",
                "operation": "upload_meal_image_immediate",
                "ai_purpose": "meal_scan",
                "image_id": image_id,
                "image_url": image_url,
                "rejection_reason": reason,
            },
        )

    async def _handle_parallel_upload(
        self,
        command: UploadMealImageImmediatelyCommand,
    ) -> Meal:
        """Upload image first, verify success, then create meal record."""
        # Step 1: Generate image ID upfront
        image_id = str(uuid4())

        # Step 2: Upload to Cloudinary FIRST (before any DB operations)
        logger.info(f"[UPLOAD-START] image_id={image_id}")
        start = time.time()

        try:
            image_url = await self.image_store.save_async(
                command.file_contents,
                command.content_type,
                image_id,
            )
        except Exception as e:
            raise RuntimeError(f"Cloudinary upload failed: {e}") from e

        # Step 3: Verify we got a valid URL back
        if not self._validate_cloudinary_url(image_url):
            raise RuntimeError("Cloudinary upload failed - invalid URL returned")

        upload_elapsed = time.time() - start
        logger.info(
            f"[UPLOAD-COMPLETE] image_id={image_id} | " f"elapsed={upload_elapsed:.2f}s"
        )

        # Step 4: Run AI analysis
        logger.info(f"[ANALYSIS-START] image_id={image_id}")
        analysis_start = time.time()

        try:
            analysis_result = await self._run_vision_analysis(command, image_id)
        except Exception as exc:
            # Image uploaded but analysis failed - acceptable orphan in Cloudinary
            if (
                isinstance(exc, AIVisionError)
                and exc.kind == AIVisionFailureKind.no_food
            ):
                self._capture_rejected_scan(
                    image_id=image_id,
                    image_url=image_url,
                    reason="vision_no_food",
                )
            increment_metric(
                "ai.vision.request.count",
                attributes={"status": "failure", "ai_purpose": "meal_scan"},
            )
            raise

        analysis_elapsed = time.time() - analysis_start
        increment_metric(
            "ai.vision.request.count",
            attributes={"status": "success", "ai_purpose": "meal_scan"},
        )
        distribution_metric(
            "ai.vision.request.duration_ms",
            analysis_elapsed * 1000,
            unit="millisecond",
            attributes={"ai_purpose": "meal_scan", "status": "success"},
        )
        logger.info(
            f"[ANALYSIS-COMPLETE] image_id={image_id} | elapsed={analysis_elapsed:.2f}s"
        )

        # Step 5: Parse nutrition and validate food detected.
        if not self.gpt_parser.parse_is_food(analysis_result):
            self._capture_rejected_scan(
                image_id=image_id,
                image_url=image_url,
                reason="parser_not_food",
            )
            raise ValueError(
                "Image does not appear to contain food. "
                "Please take a photo of food and try again."
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
            self._capture_rejected_scan(
                image_id=image_id,
                image_url=image_url,
                reason="nutrition_empty_or_zero_calorie",
            )
            raise ValueError(
                "No edible food detected in the image. "
                "Please take a photo of food and try again."
            )

        # Step 6: NOW create meal record with verified image URL
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

            meal = Meal(
                meal_id=str(uuid4()),
                user_id=command.user_id,
                status=MealStatus.READY,
                created_at=meal_datetime,
                meal_type=meal_type,
                image=MealImage(
                    image_id=image_id,
                    format="jpeg" if "jpeg" in command.content_type else "png",
                    size_bytes=len(command.file_contents),
                    url=image_url,
                ),
                source="scanner",
                dish_name=dish_name or "Unknown dish",
                emoji=self.gpt_parser.parse_emoji(analysis_result),
                ready_at=utc_now(),
                raw_gpt_json=self.gpt_parser.extract_raw_json(analysis_result),
                nutrition=nutrition,
            )

            saved_meal = await uow.meals.save(meal)
            await uow.commit()

            total_elapsed = time.time() - start
            logger.info(
                f"[MEAL-CREATED] meal={saved_meal.meal_id} | "
                f"image_id={image_id} | "
                f"total_elapsed={total_elapsed:.2f}s"
            )

        # Translation repository uses its own DB session, so the parent meal must
        # be committed before inserting meal_translation rows.
        if (
            command.language
            and command.language != "en"
            and self.meal_translation_service
            and nutrition
            and nutrition.food_items
        ):
            try:
                await self.meal_translation_service.translate_meal(
                    meal=saved_meal,
                    dish_name=saved_meal.dish_name,
                    food_items=nutrition.food_items,
                    target_language=command.language,
                )
                logger.info(
                    f"[TRANSLATION] meal={saved_meal.meal_id} translated to {command.language}"
                )
            except Exception as e:
                logger.warning(
                    f"[TRANSLATION] failed for meal={saved_meal.meal_id}: {e}"
                )

        async with self.uow as uow:
            final_meal = await uow.meals.find_by_id(
                saved_meal.meal_id, projection=MealProjection.FULL_WITH_TRANSLATIONS
            )

        if self.cache_invalidation:
            await self.cache_invalidation.after_meal_write(command.user_id, meal_date)

        return final_meal

    async def handle(self, command: UploadMealImageImmediatelyCommand) -> Meal:
        """Handle immediate meal image upload and analysis."""
        if not all([self.image_store, self.vision_service, self.gpt_parser]):
            raise RuntimeError("Required dependencies not configured")

        return await self._handle_parallel_upload(command)
