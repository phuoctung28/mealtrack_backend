import pytest

from src.domain.model.meal_image_cache import PendingItem
from src.infra.repositories.pending_meal_image_repository import (
    PendingMealImageRepository,
)


@pytest.mark.asyncio
async def test_enqueue_is_idempotent_by_slug(db_session):
    repo = PendingMealImageRepository(db_session)
    await repo.enqueue_many([
        PendingItem(meal_name="Grilled Salmon", name_slug="grilled-salmon"),
        PendingItem(meal_name="Grilled Salmon", name_slug="grilled-salmon"),  # dup
    ])
    claimed = await repo.claim_batch(10)
    assert [c.name_slug for c in claimed] == ["grilled-salmon"]


@pytest.mark.asyncio
async def test_claim_batch_returns_in_enqueue_order(db_session):
    repo = PendingMealImageRepository(db_session)
    await repo.enqueue_many([PendingItem("A", "a"), PendingItem("B", "b"),
                             PendingItem("C", "c")])
    claimed = await repo.claim_batch(2)
    assert [c.name_slug for c in claimed] == ["a", "b"]


@pytest.mark.asyncio
async def test_mark_resolved_removes_row(db_session):
    repo = PendingMealImageRepository(db_session)
    await repo.enqueue_many([PendingItem("X", "x")])
    await repo.mark_resolved("x")
    claimed = await repo.claim_batch(10)
    assert claimed == []


@pytest.mark.asyncio
async def test_mark_failed_increments_attempts(db_session):
    repo = PendingMealImageRepository(db_session)
    await repo.enqueue_many([PendingItem("Y", "y")])
    await repo.mark_failed("y", "boom")
    claimed = await repo.claim_batch(10)
    assert len(claimed) == 1
    assert claimed[0].attempts == 1
