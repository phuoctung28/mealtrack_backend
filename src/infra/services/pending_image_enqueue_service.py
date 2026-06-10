"""Enqueue pending meal images with a UoW-owned transaction."""

import logging

from src.domain.model.meal_image_cache import PendingItem
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.pending_meal_image_repository_async import (
    AsyncPendingMealImageRepository,
)

logger = logging.getLogger(__name__)


async def enqueue_pending_images(items: list[PendingItem]) -> None:
    """Persist pending image items; silently swallows errors (non-fatal path)."""
    if not items:
        return
    try:
        async with AsyncUnitOfWork() as uow:
            await AsyncPendingMealImageRepository(uow.session).enqueue_many(items)
    except Exception as e:
        logger.warning("Pending image queue enqueue failed (non-fatal): %s", e)
