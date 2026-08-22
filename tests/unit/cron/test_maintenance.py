"""Unit tests for the maintenance cron entry point."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cron.maintenance import (
    cleanup_meal_write_operations,
    cleanup_outbox_records,
    run,
)


class _FakeUow:
    def __init__(
        self,
        meal_deleted_counts: list[int] | None = None,
        outbox_deleted_counts: list[dict[str, int]] | None = None,
    ):
        self.meal_deleted_counts = list(meal_deleted_counts or [])
        self.outbox_deleted_counts = list(outbox_deleted_counts or [])
        self.meal_write_operations = MagicMock()
        self.outbox = MagicMock()
        self.commits = 0

        async def _meal_cleanup(*args, **kwargs):
            if self.meal_deleted_counts:
                return self.meal_deleted_counts.pop(0)
            return 0

        async def _outbox_cleanup(*args, **kwargs):
            if self.outbox_deleted_counts:
                return self.outbox_deleted_counts.pop(0)
            return {
                "deleted_completed": 0,
                "deleted_dead_letter": 0,
                "total_deleted": 0,
            }

        self.meal_write_operations.cleanup_finished = _meal_cleanup
        self.outbox.cleanup_outbox_records = _outbox_cleanup

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_cleanup_meal_write_operations_batches_until_exhausted():
    fake_uow = _FakeUow(meal_deleted_counts=[500, 200])

    with patch("src.cron.maintenance.AsyncUnitOfWork", return_value=fake_uow):
        total = await cleanup_meal_write_operations(
            older_than_days=30, batch_size=500, max_batches=10
        )

    assert total == 700
    assert fake_uow.commits == 2


@pytest.mark.asyncio
async def test_cleanup_outbox_records_batches_until_exhausted():
    fake_uow = _FakeUow(
        outbox_deleted_counts=[
            {
                "deleted_completed": 400,
                "deleted_dead_letter": 100,
                "total_deleted": 500,
            },
            {"deleted_completed": 50, "deleted_dead_letter": 10, "total_deleted": 60},
        ]
    )

    with patch("src.cron.maintenance.AsyncUnitOfWork", return_value=fake_uow):
        stats = await cleanup_outbox_records(
            completed_older_than_days=7,
            dead_letter_older_than_days=30,
            batch_size=500,
            max_batches=10,
        )

    assert stats["deleted_completed"] == 450
    assert stats["deleted_dead_letter"] == 110
    assert stats["total_deleted"] == 560
    assert fake_uow.commits == 2


@pytest.mark.asyncio
async def test_maintenance_cron_happy_path_runs():
    engine = MagicMock()
    connect_cm = AsyncMock()
    conn = AsyncMock()
    conn.execute = AsyncMock()
    connect_cm.__aenter__.return_value = conn
    connect_cm.__aexit__.return_value = False
    engine.connect.return_value = connect_cm
    engine.dispose = AsyncMock()

    with (
        patch("src.cron.maintenance.initialize_observability"),
        patch("src.cron.maintenance.async_engine", engine),
        patch(
            "src.cron.maintenance.cleanup_meal_write_operations",
            new_callable=AsyncMock,
            return_value=42,
        ) as mock_meal_cleanup,
        patch(
            "src.cron.maintenance.cleanup_outbox_records",
            new_callable=AsyncMock,
            return_value={
                "deleted_completed": 10,
                "deleted_dead_letter": 5,
                "total_deleted": 15,
            },
        ) as mock_outbox_cleanup,
        patch("src.cron.maintenance.flush_observability"),
    ):
        await run()

        mock_meal_cleanup.assert_awaited_once_with(older_than_days=30, batch_size=500)
        mock_outbox_cleanup.assert_awaited_once_with(
            completed_older_than_days=7,
            dead_letter_older_than_days=30,
            batch_size=500,
        )
        engine.dispose.assert_awaited_once()
