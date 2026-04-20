"""
Handler for analyzing a meal image uploaded directly to Cloudinary.

This flow avoids transferring raw image bytes through the API server.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from src.app.commands.meal.analyze_meal_from_upload_command import (
    AnalyzeMealFromUploadCommand,
)
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import Meal, MealStatus, MealImage
from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.meal_type_determination_service import (
    determine_meal_type_from_timestamp,
)
from src.domain.utils.timezone_utils import utc_now, get_zone_info, is_valid_timezone
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


def _is_allowed_cloudinary_public_id(public_id: str, folder: str) -> bool:
    normalized = public_id.strip().lstrip("/")
    folder_norm = folder.strip().strip("/")
    return normalized.startswith(f"{folder_norm}/") and ".." not in normalized


def _is_allowed_cloudinary_url(url: str, folder: str) -> bool:
    """Validate URL is a genuine Cloudinary URL containing the expected folder."""
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme != "https":
            return False
        hostname = parsed.hostname or ""
        if not hostname.endswith("cloudinary.com"):
            return False
        folder_norm = folder.strip().strip("/").lower()
        return f"/{folder_norm}/" in parsed.path.lower()
    except Exception:
        return False


@handles(AnalyzeMealFromUploadCommand)
class AnalyzeMealFromUploadCommandHandler(
    EventHandler[AnalyzeMealFromUploadCommand, Meal]
):
    def __init__(
        self,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None,
        cache_service: Optional[CacheService] = None,
    ):
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
        self.cache_service = cache_service

    def set_dependencies(self, **kwargs):
        self.vision_service = kwargs.get("vision_service", self.vision_service)
        self.gpt_parser = kwargs.get("gpt_parser", self.gpt_parser)
        self.cache_service = kwargs.get("cache_service", self.cache_service)

    async def handle(self, command: AnalyzeMealFromUploadCommand) -> Meal:
        if not all([self.vision_service, self.gpt_parser]):
            raise RuntimeError("Required dependencies not configured")

        folder = "mealtrack"

        if not _is_allowed_cloudinary_public_id(command.cloudinary_public_id, folder):
            raise ValueError("Invalid Cloudinary public_id")

        if not _is_allowed_cloudinary_url(command.cloudinary_url, folder):
            raise ValueError("Invalid Cloudinary URL")

        try:
            meal_date = command.target_date if command.target_date else utc_now().date()
            meal_datetime = datetime.combine(
                meal_date, utc_now().time(), tzinfo=timezone.utc
            )

            with UnitOfWork() as uow:
                user_timezone = uow.users.get_user_timezone(command.user_id)

            if not user_timezone or not is_valid_timezone(user_timezone):
                user_timezone = "UTC"
                logger.info("Using UTC fallback for meal type detection")

            zone_info = get_zone_info(user_timezone)
            local_datetime = meal_datetime.astimezone(zone_info)
            meal_type = determine_meal_type_from_timestamp(local_datetime)

            image_id = command.cloudinary_public_id.strip().split("/")[-1]

            meal = Meal(
                meal_id=str(uuid4()),
                user_id=command.user_id,
                status=MealStatus.ANALYZING,
                created_at=meal_datetime,
                meal_type=meal_type,
                image=MealImage(
                    image_id=image_id,
                    format="jpeg",
                    size_bytes=0,
                    url=command.cloudinary_url,
                ),
                source="scanner",
            )

            with UnitOfWork() as uow:
                saved_meal = uow.meals.save(meal)
                uow.commit()
                logger.info(
                    "Created meal record %s with ANALYZING status (direct upload)",
                    saved_meal.meal_id,
                )

            phase1_start = time.time()
            if command.user_description:
                from src.domain.strategies.meal_analysis_strategy import (
                    AnalysisStrategyFactory,
                )

                strategy = AnalysisStrategyFactory.create_user_context_strategy(
                    command.user_description
                )
                vision_result = self.vision_service.analyze_from_url_with_strategy(
                    command.cloudinary_url, strategy
                )
            else:
                vision_result = self.vision_service.analyze_from_url(command.cloudinary_url)
            phase1_elapsed = time.time() - phase1_start

            nutrition = self.gpt_parser.parse_to_nutrition(vision_result)
            dish_name = self.gpt_parser.parse_dish_name(vision_result)

            meal.dish_name = dish_name or "Unknown dish"
            meal.status = MealStatus.READY
            meal.ready_at = utc_now()
            meal.raw_gpt_json = self.gpt_parser.extract_raw_json(vision_result)
            meal.nutrition = nutrition

            with UnitOfWork() as uow:
                final_meal = uow.meals.save(meal)
                uow.commit()
                logger.info(
                    "[ANALYSIS-COMPLETE] meal=%s | elapsed=%.2fs | status=%s",
                    final_meal.meal_id,
                    phase1_elapsed,
                    final_meal.status,
                )

            await self._invalidate_daily_macros(command.user_id, meal_date)
            return final_meal

        except Exception as e:
            logger.error("Failed to analyze meal from upload: %s", e)
            if "meal" in locals() and getattr(meal, "meal_id", None):
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

        week_start = target_date - timedelta(days=target_date.weekday())
        weekly_key, _ = CacheKeys.weekly_budget(user_id, week_start)
        await self.cache_service.invalidate(weekly_key)

        # Invalidate streak and daily activities caches
        streak_key, _ = CacheKeys.user_streak(user_id)
        await self.cache_service.invalidate(streak_key)
        activities_key, _ = CacheKeys.daily_activities(user_id, target_date)
        await self.cache_service.invalidate(activities_key)
