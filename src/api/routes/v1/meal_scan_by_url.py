"""POST /v1/meals/scan-by-url — analyze a Cloudinary-hosted meal image via bytes path."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, Request, status
from pydantic import BaseModel

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ValidationException, handle_exception
from src.api.mappers.meal_mapper import MealMapper
from src.api.middleware.accept_language import get_request_language
from src.api.schemas.response import DetailedMealResponse
from src.app.commands.meal.scan_by_url_command import ScanByUrlCommand
from src.domain.services.prompts.input_sanitizer import sanitize_user_description
from typing import Any

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/meals", tags=["Meals"])

_ALLOWED_HOST = "res.cloudinary.com"


class ScanByUrlRequest(BaseModel):
    image_url: str
    image_id: str
    user_description: Optional[str] = None
    target_date: Optional[str] = None


@router.post(
    "/scan-by-url",
    status_code=status.HTTP_200_OK,
    response_model=DetailedMealResponse,
)
async def scan_meal_by_url(
    request: Request,
    body: ScanByUrlRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
    event_bus: Any = Depends(get_configured_event_bus),
):
    """Analyze a meal image already uploaded to Cloudinary via the safe bytes-download path."""
    try:
        if not body.image_url.startswith(f"https://{_ALLOWED_HOST}/"):
            raise ValidationException(
                message="image_url must be a Cloudinary res URL",
                error_code="INVALID_IMAGE_URL",
                details={"url": body.image_url},
            )

        if body.image_id not in body.image_url:
            raise ValidationException(
                message="image_id does not match image_url",
                error_code="IMAGE_ID_URL_MISMATCH",
                details={"image_id": body.image_id},
            )

        parsed_target_date = None
        if body.target_date:
            try:
                parsed_target_date = datetime.strptime(body.target_date, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValidationException(
                    message="Invalid date format. Use YYYY-MM-DD format.",
                    error_code="INVALID_DATE_FORMAT",
                    details={"date": body.target_date},
                ) from e

        sanitized_description = sanitize_user_description(body.user_description) if body.user_description else None
        language = get_request_language(request)
        public_id = f"mealtrack/{body.image_id}"

        command = ScanByUrlCommand(
            user_id=user_id,
            image_url=body.image_url,
            public_id=public_id,
            user_description=sanitized_description,
            target_date=parsed_target_date,
            language=language,
        )

        try:
            meal = await event_bus.send(command)
        except (RuntimeError, ValueError) as e:
            logger.warning("[SCAN-BY-URL] food not detected: %s", e)
            raise ValidationException(
                message="Could not identify food in the image. Please try again with a food photo.",
                error_code="NOT_FOOD_IMAGE",
                details={"error_message": str(e)},
            ) from e

        if meal.status.value == "FAILED":
            error_message = meal.error_message or "Analysis failed"
            raise ValidationException(
                message=f"Failed to analyze meal image: {error_message}",
                error_code="FAILED_TO_ANALYZE_MEAL_IMAGE",
                details={"error_message": error_message},
            )

        image_url = meal.image.url if meal.image else None
        return MealMapper.to_detailed_response(meal, image_url, target_language=language)

    except ValidationException:
        raise
    except Exception as e:
        raise handle_exception(e) from e
