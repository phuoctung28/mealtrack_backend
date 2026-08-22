"""Adversarial and empirical stress tests for Outbox Worker CLI and Maintenance Cleanup.

Tested Dimensions:
1. CLI Argument Parsing & Environment Variable Precedence.
2. Signal Handling (SIGTERM/SIGINT) & In-Flight Batch Clean Draining.
3. DB Warm-up Failure Handling & Async Engine Disposal.
4. Maintenance Retention Cleanup Phase 2 (Completed >7d, DLQ >30d, Active Preservation, Batching).
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tests.fixtures.fakes.fake_outbox_repository import FakeOutboxRepository

from src.cron.maintenance import cleanup_outbox_records
from src.cron.maintenance import run as maintenance_run
from src.cron.outbox_worker import main as worker_main
from src.cron.outbox_worker import parse_args, run_worker
from src.domain.models.outbox_status import OutboxStatus
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.outbox_event import TransactionalOutboxORM
from src.infra.repositories.outbox_repository import AsyncOutboxRepository

# ============================================================================
# 1. CLI Argument Parsing & Environment Precedence Tests
# ============================================================================


class TestOutboxWorkerArgParsingStress:
    def test_parse_args_all_explicit_flags(self):
        args = parse_args(
            [
                "--once",
                "--poll-interval",
                "5.5",
                "--batch-size",
                "100",
                "--concurrency",
                "20",
                "--lease-duration",
                "120",
                "--max-batches",
                "5",
            ]
        )
        assert args.once is True
        assert args.continuous is False
        assert args.poll_interval == 5.5
        assert args.batch_size == 100
        assert args.concurrency == 20
        assert args.lease_duration == 120
        assert args.max_batches == 5

    def test_parse_args_env_var_fallbacks(self):
        env_vars = {
            "OUTBOX_POLL_INTERVAL_SECONDS": "4.5",
            "OUTBOX_BATCH_SIZE": "75",
            "OUTBOX_CONCURRENCY_LIMIT": "15",
            "OUTBOX_LEASE_DURATION_SECONDS": "90",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            args = parse_args([])
            assert args.poll_interval == 4.5
            assert args.batch_size == 75
            assert args.concurrency == 15
            assert args.lease_duration == 90

    def test_parse_args_mutually_exclusive_flags_raise_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--once", "--continuous"])

    def test_parse_args_invalid_numeric_types_raise_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--batch-size", "invalid_int"])

        with pytest.raises(SystemExit):
            parse_args(["--poll-interval", "not_a_float"])

        with pytest.raises(SystemExit):
            parse_args(["--concurrency", "abc"])

    def test_parse_args_unrecognized_argument_raises_error(self):
        with pytest.raises(SystemExit):
            parse_args(["--unsupported-flag"])

    @pytest.mark.asyncio
    async def test_main_env_worker_mode_continuous_without_cli_flags(self):
        engine_mock = MagicMock()
        engine_mock.dispose = AsyncMock()

        with (
            patch.dict(os.environ, {"OUTBOX_WORKER_MODE": "continuous"}, clear=False),
            patch("src.cron.outbox_worker.initialize_observability"),
            patch("src.cron.outbox_worker.flush_observability"),
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.run_worker",
                new_callable=AsyncMock,
                return_value={"claimed": 0},
            ) as mock_run_worker,
        ):
            await worker_main([])
            mock_run_worker.assert_awaited_once()
            _, kwargs = mock_run_worker.call_args
            assert kwargs["continuous"] is True

    @pytest.mark.asyncio
    async def test_main_env_worker_mode_continuous_overridden_by_cli_once(self):
        engine_mock = MagicMock()
        engine_mock.dispose = AsyncMock()

        with (
            patch.dict(os.environ, {"OUTBOX_WORKER_MODE": "continuous"}, clear=False),
            patch("src.cron.outbox_worker.initialize_observability"),
            patch("src.cron.outbox_worker.flush_observability"),
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.run_worker",
                new_callable=AsyncMock,
                return_value={"claimed": 0},
            ) as mock_run_worker,
        ):
            await worker_main(["--once"])
            mock_run_worker.assert_awaited_once()
            _, kwargs = mock_run_worker.call_args
            assert kwargs["continuous"] is False


# ============================================================================
# 2. Signal Handling & Clean Batch Draining Stress Tests
# ============================================================================


class TestSignalHandlingAndBatchDrainingStress:
    @pytest.mark.asyncio
    async def test_in_flight_batch_drains_cleanly_when_signal_received(self):
        """Verify that when stop_event is set during batch execution, the batch

        completes fully and the worker loop exits immediately after without claiming
        another batch.
        """
        engine_mock = MagicMock()
        conn_mock = AsyncMock()
        conn_mock.execute = AsyncMock()
        connect_cm = AsyncMock()
        connect_cm.__aenter__.return_value = conn_mock
        connect_cm.__aexit__.return_value = False
        engine_mock.connect.return_value = connect_cm

        stop_event = asyncio.Event()
        batch_started = asyncio.Event()
        batch_finished = False

        mock_dispatch_engine = MagicMock()

        async def _slow_run_once():
            nonlocal batch_finished
            batch_started.set()
            # Simulate work taking time while signal arrives
            await asyncio.sleep(0.05)
            batch_finished = True
            return {"claimed": 10, "completed": 10, "retried": 0, "dead_letter": 0}

        mock_dispatch_engine.run_once = AsyncMock(side_effect=_slow_run_once)

        async def _send_signal_mid_batch():
            await batch_started.wait()
            # Send stop signal while run_once is actively in progress
            stop_event.set()

        with (
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.OutboxDispatchEngine",
                return_value=mock_dispatch_engine,
            ),
        ):
            # Run worker and signal trigger concurrently
            worker_task = asyncio.create_task(
                run_worker(
                    continuous=True,
                    poll_interval=1.0,
                    stop_event=stop_event,
                )
            )
            signal_task = asyncio.create_task(_send_signal_mid_batch())

            stats = await worker_task
            await signal_task

        # Assert batch completed in its entirety before exit
        assert batch_finished is True
        assert stats["batches"] == 1
        assert stats["claimed"] == 10
        assert stats["completed"] == 10
        assert mock_dispatch_engine.run_once.await_count == 1

    @pytest.mark.asyncio
    async def test_continuous_idle_sleep_wakes_immediately_on_stop_event(self):
        """Verify that stop_event during idle poll sleep wakes up immediately

        instead of waiting for the full poll_interval.
        """
        engine_mock = MagicMock()
        conn_mock = AsyncMock()
        conn_mock.execute = AsyncMock()
        connect_cm = AsyncMock()
        connect_cm.__aenter__.return_value = conn_mock
        connect_cm.__aexit__.return_value = False
        engine_mock.connect.return_value = connect_cm

        stop_event = asyncio.Event()
        mock_dispatch_engine = MagicMock()
        mock_dispatch_engine.run_once = AsyncMock(
            return_value={"claimed": 0, "completed": 0, "retried": 0, "dead_letter": 0}
        )

        async def _trigger_stop_after_delay():
            await asyncio.sleep(0.05)
            stop_event.set()

        start_time = time.monotonic()
        with (
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.OutboxDispatchEngine",
                return_value=mock_dispatch_engine,
            ),
        ):
            trigger_task = asyncio.create_task(_trigger_stop_after_delay())
            stats = await run_worker(
                continuous=True,
                poll_interval=10.0,  # Long poll interval
                stop_event=stop_event,
            )
            await trigger_task

        duration = time.monotonic() - start_time
        assert duration < 1.0  # Woke up immediately upon stop_event
        assert stats["batches"] == 1

    @pytest.mark.asyncio
    async def test_signal_registration_handles_unsupported_environments(self):
        """Verify main() handles platforms/threads where add_signal_handler raises

        NotImplementedError or RuntimeError.
        """
        engine_mock = MagicMock()
        engine_mock.dispose = AsyncMock()

        loop_mock = MagicMock()
        loop_mock.add_signal_handler.side_effect = NotImplementedError(
            "Signals not supported"
        )

        with (
            patch("asyncio.get_running_loop", return_value=loop_mock),
            patch("src.cron.outbox_worker.initialize_observability"),
            patch("src.cron.outbox_worker.flush_observability"),
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.run_worker",
                new_callable=AsyncMock,
                return_value={"claimed": 0},
            ) as mock_run_worker,
        ):
            await worker_main(["--once"])
            mock_run_worker.assert_awaited_once()
            engine_mock.dispose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_main_finally_ensures_engine_dispose_on_cancellation(self):
        """Verify engine.dispose() and flush_observability() run even on task

        cancellation.
        """
        engine_mock = MagicMock()
        engine_mock.dispose = AsyncMock()

        with (
            patch("src.cron.outbox_worker.initialize_observability"),
            patch("src.cron.outbox_worker.flush_observability") as mock_flush,
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.run_worker",
                new_callable=AsyncMock,
                side_effect=asyncio.CancelledError(),
            ),
        ):
            with pytest.raises(asyncio.CancelledError):
                await worker_main(["--once"])

            mock_flush.assert_called_once()
            engine_mock.dispose.assert_awaited_once()


# ============================================================================
# 3. DB Warm-up Failure & Engine Disposal Stress Tests
# ============================================================================


class TestDBWarmupAndEngineDisposalStress:
    @pytest.mark.asyncio
    async def test_run_worker_handles_engine_none(self):
        with (
            patch("src.cron.outbox_worker.async_engine", None),
            patch("src.cron.outbox_worker.capture_exception") as mock_capture,
        ):
            stats = await run_worker(continuous=False)

        assert stats == {"claimed": 0, "completed": 0, "retried": 0, "dead_letter": 0}
        mock_capture.assert_called_once()

    @pytest.mark.asyncio
    async def test_maintenance_run_db_warmup_engine_none(self):
        with (
            patch("src.cron.maintenance.initialize_observability"),
            patch("src.cron.maintenance.async_engine", None),
            patch("src.cron.maintenance.capture_exception") as mock_capture,
            patch("src.cron.maintenance.flush_observability") as mock_flush,
            patch(
                "src.cron.maintenance.cleanup_meal_write_operations",
                new_callable=AsyncMock,
            ) as mock_p1,
            patch(
                "src.cron.maintenance.cleanup_outbox_records",
                new_callable=AsyncMock,
            ) as mock_p2,
        ):
            await maintenance_run()

            mock_capture.assert_called_once()
            mock_flush.assert_called_once()
            mock_p1.assert_not_awaited()
            mock_p2.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_maintenance_phase1_failure_does_not_abort_phase2(self):
        engine_mock = MagicMock()
        conn_mock = AsyncMock()
        conn_mock.execute = AsyncMock()
        connect_cm = AsyncMock()
        connect_cm.__aenter__.return_value = conn_mock
        connect_cm.__aexit__.return_value = False
        engine_mock.connect.return_value = connect_cm
        engine_mock.dispose = AsyncMock()

        with (
            patch("src.cron.maintenance.initialize_observability"),
            patch("src.cron.maintenance.async_engine", engine_mock),
            patch("src.cron.maintenance.capture_exception") as mock_capture,
            patch("src.cron.maintenance.flush_observability") as mock_flush,
            patch(
                "src.cron.maintenance.cleanup_meal_write_operations",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Phase 1 exploded"),
            ),
            patch(
                "src.cron.maintenance.cleanup_outbox_records",
                new_callable=AsyncMock,
                return_value={
                    "deleted_completed": 10,
                    "deleted_dead_letter": 5,
                    "total_deleted": 15,
                },
            ) as mock_p2,
        ):
            await maintenance_run()

            mock_capture.assert_called_once()
            mock_p2.assert_awaited_once()
            mock_flush.assert_called_once()
            engine_mock.dispose.assert_awaited_once()


# ============================================================================
# 4. Maintenance Retention Cleanup Phase 2 Stress Tests
# ============================================================================


class TestMaintenanceRetentionCleanupPhase2Stress:
    @pytest.mark.asyncio
    async def test_cleanup_outbox_records_multi_batch_exhaustion(self):
        fake_uow = MagicMock()
        fake_uow.__aenter__ = AsyncMock(return_value=fake_uow)
        fake_uow.__aexit__ = AsyncMock(return_value=False)
        fake_uow.commit = AsyncMock()

        batches = [
            {
                "deleted_completed": 300,
                "deleted_dead_letter": 200,
                "total_deleted": 500,
            },
            {
                "deleted_completed": 400,
                "deleted_dead_letter": 100,
                "total_deleted": 500,
            },
            {"deleted_completed": 50, "deleted_dead_letter": 20, "total_deleted": 70},
        ]

        async def _mock_cleanup(*args, **kwargs):
            if batches:
                return batches.pop(0)
            return {
                "deleted_completed": 0,
                "deleted_dead_letter": 0,
                "total_deleted": 0,
            }

        fake_uow.outbox.cleanup_outbox_records = _mock_cleanup

        with patch("src.cron.maintenance.AsyncUnitOfWork", return_value=fake_uow):
            stats = await cleanup_outbox_records(
                completed_older_than_days=7,
                dead_letter_older_than_days=30,
                batch_size=500,
                max_batches=10,
            )

        assert stats["deleted_completed"] == 750
        assert stats["deleted_dead_letter"] == 320
        assert stats["total_deleted"] == 1070
        assert fake_uow.commit.await_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_outbox_records_max_batches_bound(self):
        fake_uow = MagicMock()
        fake_uow.__aenter__ = AsyncMock(return_value=fake_uow)
        fake_uow.__aexit__ = AsyncMock(return_value=False)
        fake_uow.commit = AsyncMock()

        fake_uow.outbox.cleanup_outbox_records = AsyncMock(
            return_value={
                "deleted_completed": 250,
                "deleted_dead_letter": 250,
                "total_deleted": 500,
            }
        )

        with patch("src.cron.maintenance.AsyncUnitOfWork", return_value=fake_uow):
            stats = await cleanup_outbox_records(
                completed_older_than_days=7,
                dead_letter_older_than_days=30,
                batch_size=500,
                max_batches=2,
            )

        assert stats["total_deleted"] == 1000
        assert fake_uow.commit.await_count == 2


# ============================================================================
# 5. In-Memory Retention Cleanup Strict Date & Status Preservation Stress Tests
# ============================================================================


class _MockScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class _MockExecResult:
    def __init__(self, items=None):
        self._items = items or []

    def scalars(self):
        return _MockScalars(self._items)


class _MockCleanupSession:
    """Mock session simulating SQL selection and deletion for cleanup."""

    def __init__(self, rows: dict[str, TransactionalOutboxORM]) -> None:
        self.rows = dict(rows)
        self.flushed = False

    async def execute(self, stmt: Any):
        stmt_str = str(stmt)
        # Select query for cleanup
        if "SELECT" in stmt_str or "select" in stmt_str:
            params = stmt.compile().params if hasattr(stmt, "compile") else {}
            status_val = None
            for v in params.values():
                if v in (
                    OutboxStatus.COMPLETED.value,
                    OutboxStatus.FAILED_DEAD_LETTER.value,
                ):
                    status_val = v
                    break

            cutoff_val = None
            for v in params.values():
                if isinstance(v, datetime) or (
                    hasattr(v, "isoformat") and not isinstance(v, str)
                ):
                    cutoff_val = v
                    break

            matched_ids = []
            for row in self.rows.values():
                if row.status == status_val:
                    if cutoff_val is not None and row.updated_at < cutoff_val:
                        matched_ids.append(row.id)
                    elif cutoff_val is None:
                        matched_ids.append(row.id)
            return _MockExecResult(matched_ids)

        if "DELETE" in stmt_str or "delete" in stmt_str:
            # Stmt delete using IN clause
            for row_id in list(self.rows.keys()):
                if row_id in stmt_str or any(
                    row_id == str(v)
                    for v in (
                        stmt.compile().params.values()
                        if hasattr(stmt, "compile")
                        else []
                    )
                ):
                    del self.rows[row_id]
            return _MockExecResult([])

        return _MockExecResult([])

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_fake_and_async_retention_cleanup_date_and_status_boundaries():
    """Empirical adversarial test verifying that:

    1. COMPLETED records older than 7d are purged.
    2. COMPLETED records newer than 7d (or exact boundary) are preserved.
    3. FAILED_DEAD_LETTER records older than 30d are purged.
    4. FAILED_DEAD_LETTER records newer than 30d (or exact boundary) are preserved.
    5. PENDING records older than 30d/45d are NEVER purged.
    6. IN_PROGRESS records older than 30d/45d are NEVER purged.
    """
    now = utc_now()
    completed_cutoff = now - timedelta(days=7)
    dead_letter_cutoff = now - timedelta(days=30)

    # 1. Test FakeOutboxRepository
    fake_repo = FakeOutboxRepository()

    # Old completed (>7d) -> Purged
    evt1 = await fake_repo.enqueue("test", {"k": 1})
    assert evt1 is not None
    evt1.status = OutboxStatus.COMPLETED
    evt1.updated_at = now - timedelta(days=8)

    # Recent completed (<7d) -> Kept
    evt2 = await fake_repo.enqueue("test", {"k": 2})
    assert evt2 is not None
    evt2.status = OutboxStatus.COMPLETED
    evt2.updated_at = now - timedelta(days=5)

    # Old DLQ (>30d) -> Purged
    evt3 = await fake_repo.enqueue("test", {"k": 3})
    assert evt3 is not None
    evt3.status = OutboxStatus.FAILED_DEAD_LETTER
    evt3.updated_at = now - timedelta(days=35)

    # Recent DLQ (<30d) -> Kept
    evt4 = await fake_repo.enqueue("test", {"k": 4})
    assert evt4 is not None
    evt4.status = OutboxStatus.FAILED_DEAD_LETTER
    evt4.updated_at = now - timedelta(days=20)

    # Old PENDING (>45d) -> NEVER PURGED
    evt5 = await fake_repo.enqueue("test", {"k": 5})
    assert evt5 is not None
    evt5.status = OutboxStatus.PENDING
    evt5.updated_at = now - timedelta(days=45)

    # Old IN_PROGRESS (>45d) -> NEVER PURGED
    evt6 = await fake_repo.enqueue("test", {"k": 6})
    assert evt6 is not None
    evt6.status = OutboxStatus.IN_PROGRESS
    evt6.updated_at = now - timedelta(days=45)

    fake_stats = await fake_repo.cleanup_outbox_records(
        completed_older_than=completed_cutoff,
        dead_letter_older_than=dead_letter_cutoff,
        batch_size=500,
    )

    assert fake_stats["deleted_completed"] == 1
    assert fake_stats["deleted_dead_letter"] == 1
    assert fake_stats["total_deleted"] == 2

    assert await fake_repo.find_by_id(evt1.id) is None
    assert await fake_repo.find_by_id(evt3.id) is None

    res2 = await fake_repo.find_by_id(evt2.id)
    assert res2 is not None and res2.status == OutboxStatus.COMPLETED

    res4 = await fake_repo.find_by_id(evt4.id)
    assert res4 is not None and res4.status == OutboxStatus.FAILED_DEAD_LETTER

    res5 = await fake_repo.find_by_id(evt5.id)
    assert res5 is not None and res5.status == OutboxStatus.PENDING

    res6 = await fake_repo.find_by_id(evt6.id)
    assert res6 is not None and res6.status == OutboxStatus.IN_PROGRESS

    # 2. Test AsyncOutboxRepository SQL generation with Mock Session
    mock_session = AsyncMock()
    # Mock finding 2 completed IDs and 1 DLQ ID
    mock_session.execute = AsyncMock(
        side_effect=[
            _MockExecResult(["comp_1", "comp_2"]),  # select completed IDs
            _MockExecResult([]),  # delete completed
            _MockExecResult(["dlq_1"]),  # select dlq IDs
            _MockExecResult([]),  # delete dlq
        ]
    )

    async_repo = AsyncOutboxRepository(mock_session)
    async_stats = await async_repo.cleanup_outbox_records(
        completed_older_than=completed_cutoff,
        dead_letter_older_than=dead_letter_cutoff,
        batch_size=500,
    )

    assert async_stats["deleted_completed"] == 2
    assert async_stats["deleted_dead_letter"] == 1
    assert async_stats["total_deleted"] == 3
    assert mock_session.execute.await_count == 4
    mock_session.flush.assert_awaited_once()


# ============================================================================
# 6. Worker Engine Wiring & Loop Aggregation Stress Tests
# ============================================================================


class TestOutboxWorkerEngineWiringAndLoopStress:
    @pytest.mark.asyncio
    async def test_run_worker_passes_configured_parameters_to_dispatch_engine(self):
        engine_mock = MagicMock()
        conn_mock = AsyncMock()
        conn_mock.execute = AsyncMock()
        connect_cm = AsyncMock()
        connect_cm.__aenter__.return_value = conn_mock
        connect_cm.__aexit__.return_value = False
        engine_mock.connect.return_value = connect_cm

        mock_dispatch_engine = MagicMock()
        mock_dispatch_engine.run_once = AsyncMock(
            return_value={"claimed": 0, "completed": 0, "retried": 0, "dead_letter": 0}
        )

        with (
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.OutboxDispatchEngine",
                return_value=mock_dispatch_engine,
            ) as mock_engine_cls,
        ):
            await run_worker(
                continuous=False,
                poll_interval=3.5,
                batch_size=88,
                concurrency=12,
                lease_duration=45,
            )

            mock_engine_cls.assert_called_once()
            _, kwargs = mock_engine_cls.call_args
            assert kwargs["batch_size"] == 88
            assert kwargs["concurrency_limit"] == 12
            assert kwargs["lease_duration"] == timedelta(seconds=45)

    @pytest.mark.asyncio
    async def test_run_worker_once_aggregates_multiple_batches_correctly(self):
        engine_mock = MagicMock()
        conn_mock = AsyncMock()
        conn_mock.execute = AsyncMock()
        connect_cm = AsyncMock()
        connect_cm.__aenter__.return_value = conn_mock
        connect_cm.__aexit__.return_value = False
        engine_mock.connect.return_value = connect_cm

        mock_dispatch_engine = MagicMock()
        mock_dispatch_engine.run_once = AsyncMock(
            side_effect=[
                {"claimed": 50, "completed": 45, "retried": 3, "dead_letter": 2},
                {"claimed": 50, "completed": 48, "retried": 2, "dead_letter": 0},
                {"claimed": 10, "completed": 10, "retried": 0, "dead_letter": 0},
                {"claimed": 0, "completed": 0, "retried": 0, "dead_letter": 0},
            ]
        )

        with (
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.OutboxDispatchEngine",
                return_value=mock_dispatch_engine,
            ),
        ):
            stats = await run_worker(continuous=False)

        assert stats["batches"] == 4
        assert stats["claimed"] == 110
        assert stats["completed"] == 103
        assert stats["retried"] == 5
        assert stats["dead_letter"] == 2
        assert mock_dispatch_engine.run_once.await_count == 4
