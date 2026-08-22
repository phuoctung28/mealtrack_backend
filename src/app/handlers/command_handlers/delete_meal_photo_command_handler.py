"""Handler for detaching uploaded meal photos."""

from typing import Any

from src.api.exceptions import AuthorizationException, ResourceNotFoundException
from src.app.commands.meal import DeleteMealPhotoCommand
from src.app.events.base import EventHandler, handles
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.domain.model.meal_projection import MealProjection
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now


@handles(DeleteMealPhotoCommand)
class DeleteMealPhotoCommandHandler(
    EventHandler[DeleteMealPhotoCommand, dict[str, Any]]
):
    """Detach a meal photo from a meal owned by the user."""

    def __init__(
        self,
        uow: AsyncUnitOfWorkPort,
        cache_invalidation: CacheInvalidationService | None = None,
    ):
        self.uow = uow
        self.cache_invalidation = cache_invalidation

    async def handle(self, command: DeleteMealPhotoCommand) -> dict[str, Any]:
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

                saved_meal = await uow.meals.save(meal.without_image())
                meal_date = (saved_meal.created_at or utc_now()).date()
                if self.cache_invalidation:
                    await self.cache_invalidation.enqueue_meal_invalidation(
                        uow.outbox,
                        saved_meal.user_id,
                        meal_date,
                    )
                await uow.commit()

                response = {
                    "success": True,
                    "meal_id": saved_meal.meal_id,
                    "image_url": None,
                }
            except Exception:
                await uow.rollback()
                raise

        return response
