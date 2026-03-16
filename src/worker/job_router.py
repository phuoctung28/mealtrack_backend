from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.api.dependencies.event_bus import get_configured_event_bus
from src.app.commands.meal import UploadMealImageImmediatelyCommand
from src.app.commands.meal_suggestion import GenerateMealSuggestionsCommand
from src.domain.model.job_queue import JobPayload

logger = logging.getLogger(__name__)


class JobRouter:
    """Route queue jobs to existing CQRS command handlers via the event bus."""

    async def handle(self, job: JobPayload) -> Any:
        """
        Dispatch a job to the appropriate command handler.

        Raises:
            ValueError: If the job type is not supported or payload is invalid.
        """
        event_bus = get_configured_event_bus()

        if job.job_type == "meal_image_analysis":
            command = self._build_meal_image_analysis_command(job)
            logger.info("Dispatching meal_image_analysis job %s", job.job_id)
            return await event_bus.send(command)

        if job.job_type == "meal_suggestions":
            command = self._build_meal_suggestions_command(job)
            logger.info("Dispatching meal_suggestions job %s", job.job_id)
            return await event_bus.send(command)

        logger.warning("Unsupported job_type '%s' for job %s", job.job_type, job.job_id)
        raise ValueError(f"Unsupported job_type '{job.job_type}'")

    @staticmethod
    def _build_meal_image_analysis_command(job: JobPayload) -> UploadMealImageImmediatelyCommand:
        payload = job.payload or {}
        target_date = payload.get("target_date")
        if isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)
        if "file_contents" in payload and "content_type" in payload:
            return UploadMealImageImmediatelyCommand(
                user_id=job.user_id,
                file_contents=payload["file_contents"],
                content_type=payload["content_type"],
                target_date=target_date,
                language=payload.get("language", "en"),
                user_description=payload.get("user_description"),
            )

        required = ("meal_id", "image_id", "content_type")
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValueError(
                f"Missing required field(s) for meal_image_analysis: {', '.join(missing)}"
            )

        return UploadMealImageImmediatelyCommand(
            user_id=job.user_id,
            meal_id=payload["meal_id"],
            image_id=payload["image_id"],
            image_url=payload.get("image_url"),
            content_type=payload["content_type"],
            target_date=target_date,
            language=payload.get("language", "en"),
            user_description=payload.get("user_description"),
        )

    @staticmethod
    def _build_meal_suggestions_command(job: JobPayload) -> GenerateMealSuggestionsCommand:
        payload = job.payload or {}

        try:
            meal_type = payload["meal_type"]
            meal_portion_type = payload["meal_portion_type"]
            ingredients = payload["ingredients"]
        except KeyError as exc:
            raise ValueError(f"Missing required field for meal_suggestions: {exc}") from exc

        return GenerateMealSuggestionsCommand(
            user_id=job.user_id,
            meal_type=meal_type,
            meal_portion_type=meal_portion_type,
            ingredients=ingredients,
            time_available_minutes=payload.get("time_available_minutes"),
            session_id=payload.get("session_id"),
            language=payload.get("language", "en"),
            servings=payload.get("servings", 1),
            cooking_equipment=payload.get("cooking_equipment"),
            cuisine_region=payload.get("cuisine_region"),
            calorie_target=payload.get("calorie_target"),
            protein_target=payload.get("protein_target"),
            carbs_target=payload.get("carbs_target"),
            fat_target=payload.get("fat_target"),
        )

