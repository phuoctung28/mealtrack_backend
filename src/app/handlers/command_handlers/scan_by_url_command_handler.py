"""Handler for scan-by-url: download Cloudinary image → compress → AI bytes path."""

import asyncio
import logging
import time
from typing import Any
from uuid import uuid4

import httpx

from src.app.commands.meal.scan_by_url_command import ScanByUrlCommand
from src.app.events.base import EventHandler, handles
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.domain.constants import MealDefaults
from src.domain.model.meal import Meal, MealImage, MealStatus
from src.domain.model.meal_projection import MealProjection
from src.domain.parsers.vision_response_parser import (
    VisionResponseParser as GPTResponseParser,
)
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.food_label_ocr_parser import FoodLabelOcrParser
from src.domain.services.meal_analysis.deepl_meal_translation_service import (
    DeepLMealTranslationService,
)
from src.domain.services.meal_type_determination_service import (
    determine_meal_type_from_timestamp,
)
from src.domain.utils.image_compression import compress_image
from src.domain.utils.timezone_utils import (
    get_zone_info,
    is_valid_timezone,
    noon_utc_for_date,
    utc_now,
)
from src.infra.config.settings import get_settings
from src.observability import capture_message, distribution_metric, increment_metric

logger = logging.getLogger(__name__)


@handles(ScanByUrlCommand)
class ScanByUrlCommandHandler(EventHandler[ScanByUrlCommand, Meal]):
    """Download Cloudinary image → compress → AI bytes path → persist Meal."""

    def __init__(
        self,
        uow: AsyncUnitOfWorkPort,
        event_bus: Any,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None,
        meal_translation_service: DeepLMealTranslationService | None = None,
        cache_invalidation: CacheInvalidationService | None = None,
        food_label_ocr_parser: FoodLabelOcrParser | None = None,
    ):
        self.uow = uow
        self.event_bus = event_bus
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
        self.meal_translation_service = meal_translation_service
        self.cache_invalidation = cache_invalidation
        self.food_label_ocr_parser = food_label_ocr_parser or FoodLabelOcrParser()

    def _record_ocr_metric(
        self,
        name: str,
        *,
        reason: str | None = None,
        elapsed_ms: float | None = None,
    ) -> None:
        attributes = {"component": "food_label_ocr"}
        if reason:
            attributes["reason"] = reason
        increment_metric(name, attributes=attributes)
        if elapsed_ms is not None:
            distribution_metric(
                "food_label_ocr.parse_latency_ms",
                elapsed_ms,
                unit="millisecond",
                attributes=attributes,
            )

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
                "operation": "scan_by_url",
                "ai_purpose": "meal_scan",
                "image_id": image_id,
                "image_url": image_url,
                "rejection_reason": reason,
            },
        )

    async def handle(self, command: ScanByUrlCommand) -> Meal:
        if not all([self.vision_service, self.gpt_parser]):
            raise RuntimeError("Required dependencies not configured")

        start = time.time()
        image_id = command.public_id.split("/")[-1]

        try:
            # Download from Cloudinary and compress off the event loop
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(command.image_url)
                resp.raise_for_status()
            raw_bytes = resp.content
            image_bytes = await asyncio.to_thread(compress_image, raw_bytes)
            logger.info(
                "[SCAN-BY-URL] image_id=%s raw=%d compressed=%d bytes",
                image_id,
                len(raw_bytes),
                len(image_bytes),
            )

            # Determine timezone-aware datetime
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
            meal_type = determine_meal_type_from_timestamp(
                meal_datetime.astimezone(zone_info)
            )

            # Vision analysis via bytes path (never sends URL to the AI provider)
            if command.scan_mode == "food_label":
                ocr_started = time.time()
                ocr_enabled = get_settings().FOOD_LABEL_OCR_FIRST_ENABLED
                has_ocr_text = bool(command.ocr_text_lines)
                if ocr_enabled and has_ocr_text:
                    self._record_ocr_metric("food_label_ocr.attempt")
                    ocr_result = self.food_label_ocr_parser.parse(
                        command.ocr_text_lines
                    )
                    elapsed_ms = (time.time() - ocr_started) * 1000
                    if ocr_result.succeeded:
                        self._record_ocr_metric(
                            "food_label_ocr.success",
                            elapsed_ms=elapsed_ms,
                        )
                        self._record_ocr_metric("food_label_ocr.ai_avoided")
                        vision_result = {"structured_data": ocr_result.structured_data}
                    else:
                        reason = ",".join(ocr_result.failure_reasons[:3])
                        self._record_ocr_metric(
                            "food_label_ocr.fallback_to_ai",
                            reason=reason or "unknown",
                            elapsed_ms=elapsed_ms,
                        )
                        vision_result = await self.vision_service.analyze_food_label(
                            image_bytes
                        )
                else:
                    self._record_ocr_metric(
                        "food_label_ocr.skipped",
                        reason="disabled" if not ocr_enabled else "no_ocr_text",
                    )
                    vision_result = await self.vision_service.analyze_food_label(
                        image_bytes
                    )
            elif command.user_description:
                from src.domain.strategies.meal_analysis_strategy import (
                    AnalysisStrategyFactory,
                )

                strategy = AnalysisStrategyFactory.create_user_context_strategy(
                    command.user_description
                )
                vision_result = await self.vision_service.analyze_with_strategy(
                    image_bytes, strategy
                )
            else:
                vision_result = await self.vision_service.analyze(image_bytes)

            vision_elapsed = time.time() - start

            if command.scan_mode == "food_label":
                nutrition = self.gpt_parser.parse_food_label_to_nutrition(vision_result)
                label_metadata = self.gpt_parser.parse_food_label_metadata(
                    vision_result
                )
                if not label_metadata.get("is_food_label", True):
                    raise ValueError(
                        "Nutrition Facts label could not be read. "
                        "Please retake the label photo and try again."
                    )

                meal = Meal(
                    meal_id=str(uuid4()),
                    user_id=command.user_id,
                    status=MealStatus.READY,
                    created_at=meal_datetime,
                    meal_type=meal_type,
                    image=MealImage(
                        image_id=image_id,
                        format="jpeg",
                        size_bytes=len(raw_bytes),
                        url=command.image_url,
                    ),
                    source="food_label",
                    dish_name=MealDefaults.UNNAMED_FOOD_NAME,
                    ready_at=utc_now(),
                    raw_gpt_json=self.gpt_parser.extract_raw_json(vision_result),
                    food_label_metadata=label_metadata,
                    nutrition=nutrition,
                )

                async with self.uow as uow:
                    saved_meal = await uow.meals.save(meal)
                    await uow.commit()

                logger.info(
                    "[SCAN-BY-URL-FOOD-LABEL-COMPLETE] meal=%s vision=%.2fs total=%.2fs",
                    saved_meal.meal_id,
                    vision_elapsed,
                    time.time() - start,
                )

                if self.cache_invalidation:
                    await self.cache_invalidation.after_meal_write(
                        command.user_id, meal_date
                    )

                return saved_meal

            if not self.gpt_parser.parse_is_food(vision_result):
                self._capture_rejected_scan(
                    image_id=image_id,
                    image_url=command.image_url,
                    reason="parser_not_food",
                )
                raise ValueError(
                    "Image does not appear to contain food. "
                    "Please take a photo of food and try again."
                )

            nutrition = self.gpt_parser.parse_to_nutrition(vision_result)
            dish_name = self.gpt_parser.parse_dish_name(vision_result)

            has_food = (
                nutrition
                and nutrition.food_items
                and len(nutrition.food_items) > 0
                and nutrition.calories > 0
            )
            if not has_food:
                self._capture_rejected_scan(
                    image_id=image_id,
                    image_url=command.image_url,
                    reason="nutrition_empty_or_zero_calorie",
                )
                raise ValueError(
                    "No edible food detected in the image. "
                    "Please take a photo of food and try again."
                )

            meal = Meal(
                meal_id=str(uuid4()),
                user_id=command.user_id,
                status=MealStatus.READY,
                created_at=meal_datetime,
                meal_type=meal_type,
                image=MealImage(
                    image_id=image_id,
                    format="jpeg",
                    size_bytes=len(raw_bytes),
                    url=command.image_url,
                ),
                source="scanner",
                dish_name=dish_name or "Unknown dish",
                emoji=self.gpt_parser.parse_emoji(vision_result),
                ready_at=utc_now(),
                raw_gpt_json=self.gpt_parser.extract_raw_json(vision_result),
                nutrition=nutrition,
            )

            async with self.uow as uow:
                saved_meal = await uow.meals.save(meal)
                await uow.commit()

            logger.info(
                "[SCAN-BY-URL-COMPLETE] meal=%s vision=%.2fs total=%.2fs",
                saved_meal.meal_id,
                vision_elapsed,
                time.time() - start,
            )

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
                except Exception as exc:
                    logger.warning(
                        "[SCAN-BY-URL] translation failed meal=%s: %s",
                        saved_meal.meal_id,
                        exc,
                    )

            async with self.uow as uow:
                final_meal = await uow.meals.find_by_id(
                    meal.meal_id, projection=MealProjection.FULL_WITH_TRANSLATIONS
                )

            if self.cache_invalidation:
                await self.cache_invalidation.after_meal_write(
                    command.user_id, meal_date
                )

            return final_meal

        except Exception:
            raise
