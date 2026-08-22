"""Handler for attaching uploaded meal photos."""

from typing import Any

from src.api.exceptions import (
    AuthorizationException,
    ResourceNotFoundException,
    ValidationException,
)
from src.app.commands.meal import AttachMealPhotoCommand
from src.app.events.base import EventHandler, handles
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.domain.model.meal import MealImage, MealStatus
from src.domain.model.meal_projection import MealProjection
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now


@handles(AttachMealPhotoCommand)
class AttachMealPhotoCommandHandler(
    EventHandler[AttachMealPhotoCommand, dict[str, Any]]
):
    """Attach a validated uploaded photo to a meal owned by the user."""

    def __init__(
        self,
        uow: AsyncUnitOfWorkPort,
        cache_invalidation: CacheInvalidationService | None = None,
    ):
        self.uow = uow
        self.cache_invalidation = cache_invalidation

    async def handle(self, command: AttachMealPhotoCommand) -> dict[str, Any]:
        async with self.uow as uow:
            try:
                meal = await uow.meals.find_by_id(
                    command.meal_id, projection=MealProjection.FULL
                )
                if not meal:
                    raise ResourceNotFoundException("Meal not found")
                if meal.user_id != command.user_id:
                    raise AuthorizationException(
                        "You do not have permission to modify this meal"
                    )
                if meal.status != MealStatus.READY:
                    raise ValidationException(
                        "Meal must be in READY status to attach a photo"
                    )

                image = MealImage(
                    image_id=command.image_id,
                    format=command.image_format,
                    size_bytes=command.size_bytes,
                    url=command.image_url,
                )
                updated_meal = meal.with_image(image)
                saved_meal = await uow.meals.save(updated_meal)
                await uow.commit()

                meal_date = (saved_meal.created_at or utc_now()).date()
                response = {
                    "success": True,
                    "meal_id": saved_meal.meal_id,
                    "image_url": saved_meal.image.url if saved_meal.image else None,
                }
            except Exception:
                await uow.rollback()
                raise

        if self.cache_invalidation:
            await self.cache_invalidation.after_meal_write(
                saved_meal.user_id, meal_date
            )
        return response
