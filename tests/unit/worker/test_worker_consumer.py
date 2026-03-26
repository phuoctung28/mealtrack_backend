from __future__ import annotations

from typing import Any, Iterable, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.model.job_queue import JobPayload
from src.worker.consumer import WorkerConsumer


class _FakeQueue:
    def __init__(self, jobs: list[JobPayload]) -> None:
        self._jobs = jobs
        self.acked: list[str] = []
        self.nacked: list[tuple[str, str]] = []

    async def dequeue(self, job_types: list[str], block_ms: int = 5000) -> Optional[JobPayload]:
        del job_types, block_ms
        if not self._jobs:
            return None
        return self._jobs.pop(0)

    async def ack(self, job_id: str) -> None:
        self.acked.append(job_id)

    async def nack(self, job_id: str, error: str) -> None:
        self.nacked.append((job_id, error))


@pytest.mark.asyncio
async def test_worker_consumer_ack_on_success(monkeypatch: pytest.MonkeyPatch):
    job = JobPayload(job_type="meal_suggestions", user_id="u1", payload={"meal_type": "lunch", "meal_portion_type": "regular", "ingredients": []})
    queue = _FakeQueue([job])

    async def fake_initialize() -> None:
        return None

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setenv("QUEUE_ENABLED", "true")

    with patch("src.worker.consumer.initialize_queue_layer", new=fake_initialize), patch(
        "src.worker.consumer.shutdown_queue_layer", new=fake_shutdown
    ), patch("src.worker.consumer.get_job_queue", return_value=queue), patch(
        "src.worker.consumer.JobRouter"
    ) as router_cls:
        router_instance = AsyncMock()
        router_cls.return_value = router_instance

        consumer = WorkerConsumer(job_types=[job.job_type], block_ms=10)

        async def stop_after_one(*args: Any, **kwargs: Any) -> None:  # noqa: ARG001
            consumer.request_stop()

        router_instance.handle.side_effect = stop_after_one

        await consumer.run()

    assert queue.acked == [job.job_id]
    assert queue.nacked == []


@pytest.mark.asyncio
async def test_worker_consumer_nack_on_failure(monkeypatch: pytest.MonkeyPatch):
    job = JobPayload(job_type="meal_suggestions", user_id="u1", payload={"meal_type": "lunch", "meal_portion_type": "regular", "ingredients": []})
    queue = _FakeQueue([job])

    async def fake_initialize() -> None:
        return None

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setenv("QUEUE_ENABLED", "true")

    with patch("src.worker.consumer.initialize_queue_layer", new=fake_initialize), patch(
        "src.worker.consumer.shutdown_queue_layer", new=fake_shutdown
    ), patch("src.worker.consumer.get_job_queue", return_value=queue), patch(
        "src.worker.consumer.JobRouter"
    ) as router_cls:
        router_instance = AsyncMock()
        router_cls.return_value = router_instance
        router_instance.handle.side_effect = RuntimeError("boom")

        consumer = WorkerConsumer(job_types=[job.job_type], block_ms=10)

        # Stop after first loop iteration
        original_process_job = consumer._process_job

        async def wrapped_process(queue_param: Any, job_param: JobPayload) -> None:
            await original_process_job(queue_param, job_param)
            consumer.request_stop()

        consumer._process_job = wrapped_process  # type: ignore[assignment]

        await consumer.run()

    assert queue.acked == []
    assert len(queue.nacked) == 1
    assert queue.nacked[0][0] == job.job_id

