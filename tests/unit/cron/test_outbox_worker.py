"""Unit tests for the transactional outbox worker CLI and background runner."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cron.outbox_worker import main, parse_args, run_worker


class TestOutboxWorkerArgs:
    def test_parse_args_defaults(self):
        args = parse_args([])
        assert args.once is False
        assert args.continuous is False
        assert args.poll_interval == 2.0
        assert args.batch_size == 50
        assert args.concurrency == 10
        assert args.lease_duration == 60
        assert args.max_batches is None

    def test_parse_args_custom(self):
        args = parse_args(
            [
                "--continuous",
                "--poll-interval",
                "1.5",
                "--batch-size",
                "25",
                "--concurrency",
                "5",
                "--lease-duration",
                "30",
                "--max-batches",
                "3",
            ]
        )
        assert args.continuous is True
        assert args.once is False
        assert args.poll_interval == 1.5
        assert args.batch_size == 25
        assert args.concurrency == 5
        assert args.lease_duration == 30
        assert args.max_batches == 3

    def test_parse_args_mutually_exclusive_modes(self):
        with pytest.raises(SystemExit):
            parse_args(["--once", "--continuous"])


class TestOutboxWorkerExecution:
    @pytest.mark.asyncio
    async def test_run_worker_db_warmup_failure(self):
        engine_mock = MagicMock()
        engine_mock.connect = MagicMock(side_effect=RuntimeError("DB unreachable"))

        with (
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch("src.cron.outbox_worker.capture_exception") as mock_capture,
        ):
            stats = await run_worker(continuous=False)

        assert stats == {"claimed": 0, "completed": 0, "retried": 0, "dead_letter": 0}
        mock_capture.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_worker_once_mode_drains_until_empty(self):
        engine_mock = MagicMock()
        conn_mock = AsyncMock()
        conn_mock.execute = AsyncMock()
        connect_cm = AsyncMock()
        connect_cm.__aenter__.return_value = conn_mock
        connect_cm.__aexit__.return_value = False
        engine_mock.connect.return_value = connect_cm

        mock_dispatch_engine = MagicMock()
        # Batch 1 returns 5 claimed, Batch 2 returns 0 claimed
        mock_dispatch_engine.run_once = AsyncMock(
            side_effect=[
                {"claimed": 5, "completed": 5, "retried": 0, "dead_letter": 0},
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

        assert stats["batches"] == 2
        assert stats["claimed"] == 5
        assert stats["completed"] == 5
        assert mock_dispatch_engine.run_once.await_count == 2

    @pytest.mark.asyncio
    async def test_run_worker_once_mode_reaches_max_batches(self):
        engine_mock = MagicMock()
        conn_mock = AsyncMock()
        conn_mock.execute = AsyncMock()
        connect_cm = AsyncMock()
        connect_cm.__aenter__.return_value = conn_mock
        connect_cm.__aexit__.return_value = False
        engine_mock.connect.return_value = connect_cm

        mock_dispatch_engine = MagicMock()
        mock_dispatch_engine.run_once = AsyncMock(
            return_value={
                "claimed": 10,
                "completed": 10,
                "retried": 0,
                "dead_letter": 0,
            }
        )

        with (
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.OutboxDispatchEngine",
                return_value=mock_dispatch_engine,
            ),
        ):
            stats = await run_worker(continuous=False, max_batches=2)

        assert stats["batches"] == 2
        assert stats["claimed"] == 20
        assert stats["completed"] == 20
        assert mock_dispatch_engine.run_once.await_count == 2

    @pytest.mark.asyncio
    async def test_run_worker_continuous_mode_polls_and_stops_on_event(self):
        engine_mock = MagicMock()
        conn_mock = AsyncMock()
        conn_mock.execute = AsyncMock()
        connect_cm = AsyncMock()
        connect_cm.__aenter__.return_value = conn_mock
        connect_cm.__aexit__.return_value = False
        engine_mock.connect.return_value = connect_cm

        stop_event = asyncio.Event()

        mock_dispatch_engine = MagicMock()

        async def _run_once_side_effect():
            # Stop worker after first iteration
            stop_event.set()
            return {"claimed": 0, "completed": 0, "retried": 0, "dead_letter": 0}

        mock_dispatch_engine.run_once = AsyncMock(side_effect=_run_once_side_effect)

        with (
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.OutboxDispatchEngine",
                return_value=mock_dispatch_engine,
            ),
        ):
            stats = await run_worker(
                continuous=True,
                poll_interval=0.01,
                stop_event=stop_event,
            )

        assert stats["batches"] == 1
        assert mock_dispatch_engine.run_once.await_count == 1


class TestOutboxWorkerMain:
    @pytest.mark.asyncio
    async def test_main_runs_and_cleans_up_resources(self):
        engine_mock = MagicMock()
        engine_mock.dispose = AsyncMock()

        with (
            patch("src.cron.outbox_worker.initialize_observability") as mock_init_obs,
            patch("src.cron.outbox_worker.flush_observability") as mock_flush_obs,
            patch("src.cron.outbox_worker.async_engine", engine_mock),
            patch(
                "src.cron.outbox_worker.run_worker",
                new_callable=AsyncMock,
                return_value={"claimed": 0},
            ) as mock_run_worker,
        ):
            await main(["--once"])

            mock_init_obs.assert_called_once()
            mock_run_worker.assert_awaited_once()
            mock_flush_obs.assert_called_once()
            engine_mock.dispose.assert_awaited_once()
