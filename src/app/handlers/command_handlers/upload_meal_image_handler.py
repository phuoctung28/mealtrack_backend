"""
Handler for uploading meal images.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from src.app.commands.meal import UploadMealImageCommand
from src.app.events.base import EventHandler, handles
from src.app.events.meal import MealImageUploadedEvent
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_image import MealImage
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort

logger = logging.getLogger(__name__)


@handles(UploadMealImageCommand)
class UploadMealImageCommandHandler(EventHandler[UploadMealImageCommand, Dict[str, Any]]):
    """Handler for uploading meal images."""

    def __init__(self, meal_repository: MealRepositoryPort = None, image_store: ImageStorePort = None):
        self.meal_repository = meal_repository
        self.image_store = image_store

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.meal_repository = kwargs.get('meal_repository', self.meal_repository)
        self.image_store = kwargs.get('image_store', self.image_store)

    async def handle(self, command: UploadMealImageCommand) -> Dict[str, Any]:
        """Upload meal image and create meal record."""
        if not self.meal_repository or not self.image_store:
            raise RuntimeError("Dependencies not configured")

        # Upload image
        image_id = self.image_store.save(
            command.file_contents,
            command.content_type
        )

        # Get image URL
        image_url = self.image_store.get_url(image_id)

        # Create meal image
        meal_image = MealImage(
            image_id=image_id,
            format="jpeg" if command.content_type == "image/jpeg" else "png",
            size_bytes=len(command.file_contents),
            url=image_url or f"mock://images/{image_id}"
        )

        # Create meal
        meal = Meal(
            meal_id=str(uuid4()),
            user_id=command.user_id,
            status=MealStatus.PROCESSING,
            created_at=datetime.now(),
            image=meal_image
        )

        # Save meal
        saved_meal = self.meal_repository.save(meal)

        return {
            "meal_id": saved_meal.meal_id,
            "status": saved_meal.status.value,
            "image_url": saved_meal.image.url if saved_meal.image else None,
            "events": [
                MealImageUploadedEvent(
                    aggregate_id=saved_meal.meal_id,
                    meal_id=saved_meal.meal_id,
                    image_url=meal_image.url,
                    upload_timestamp=datetime.now()
                )
            ]
        }
