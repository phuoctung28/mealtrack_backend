from unittest.mock import AsyncMock

import pytest

from src.domain.model.meal_image_cache import PendingItem
from src.infra.repositories.pending_meal_image_repository_async import (
    AsyncPendingMealImageRepository,
)


class _AsyncSession:
    def __init__(self):
        self.execute = AsyncMock()
        self.flush = AsyncMock()


@pytest.mark.asyncio
async def test_enqueue_many_flushes_without_committing():
    session = _AsyncSession()
    repo = AsyncPendingMealImageRepository(session)

    await repo.enqueue_many(
        [PendingItem(meal_name="Grilled Salmon", name_slug="grilled-salmon")]
    )

    session.execute.assert_awaited_once()
    session.flush.assert_awaited_once()
    assert not hasattr(session, "commit")


@pytest.mark.asyncio
async def test_enqueue_many_empty_items_does_not_flush():
    session = _AsyncSession()
    repo = AsyncPendingMealImageRepository(session)

    await repo.enqueue_many([])

    session.execute.assert_not_awaited()
    session.flush.assert_not_awaited()
