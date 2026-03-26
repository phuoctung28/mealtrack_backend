from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import pytest

from src.domain.model.job_queue import JobPayload, JobStatus
from src.infra.queue.redis_job_queue import RedisJobQueue


@dataclass
class _FakeRedisClientWrapper:
    client: Any


class _FakeRedis:
    def __init__(self):
        self._id_counter = 0
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
        self.groups: set[tuple[str, str]] = set()
        self.state: dict[str, dict[str, str]] = {}
        self.pending: dict[str, str] = {}  # stream_id -> stream_name
        self.zsets: dict[str, dict[str, float]] = defaultdict(dict)
        self.counters: dict[str, int] = defaultdict(int)

    async def xgroup_create(self, name: str, groupname: str, id: str, mkstream: bool):
        del id, mkstream
        self.groups.add((name, groupname))

    async def xadd(self, stream_name: str, fields: dict[str, str]):
        self._id_counter += 1
        stream_id = f"{self._id_counter}-0"
        self.streams[stream_name].append((stream_id, deepcopy(fields)))
        return stream_id

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int = 1,
        block: int | None = None,
    ):
        del groupname, consumername, count, block
        stream_name = next(iter(streams.keys()))
        if not self.streams[stream_name]:
            return []
        stream_id, fields = self.streams[stream_name].pop(0)
        self.pending[stream_id] = stream_name
        return [(stream_name, [(stream_id, deepcopy(fields))])]

    async def xack(self, stream_name: str, group_name: str, stream_id: str):
        del stream_name, group_name
        self.pending.pop(stream_id, None)
        return 1

    async def xdel(self, stream_name: str, stream_id: str):
        del stream_name, stream_id
        return 1

    async def hset(self, key: str, mapping: dict[str, str]):
        self.state[key] = dict(mapping)
        return 1

    async def hgetall(self, key: str):
        return dict(self.state.get(key, {}))

    async def zadd(self, key: str, mapping: dict[str, float]):
        self.zsets[key].update(mapping)
        return len(mapping)

    async def zrangebyscore(self, key: str, min_score: float, max_score: float):
        members = []
        for member, score in self.zsets.get(key, {}).items():
            if min_score <= score <= max_score:
                members.append(member)
        return members

    async def zrem(self, key: str, member: str):
        self.zsets[key].pop(member, None)
        return 1

    async def zpopmin(self, key: str, count: int = 1):
        z = self.zsets.get(key, {})
        if not z:
            return []
        sorted_items = sorted(z.items(), key=lambda x: x[1])[:count]
        for member, _ in sorted_items:
            self.zsets[key].pop(member, None)
        return sorted_items

    async def incr(self, key: str):
        self.counters[key] += 1
        return self.counters[key]


@pytest.mark.asyncio
async def test_enqueue_dequeue_ack_status_lifecycle():
    fake = _FakeRedis()
    queue = RedisJobQueue(
        redis_client=_FakeRedisClientWrapper(client=fake),
        consumer_name="test-consumer",
    )

    job = JobPayload(
        job_type="meal_image_analysis",
        user_id="user-1",
        payload={"meal_id": "meal-1"},
    )
    job_id = await queue.enqueue(job)
    assert job_id == job.job_id
    assert await queue.get_status(job_id) == JobStatus.QUEUED

    dequeued = await queue.dequeue(["meal_image_analysis"])
    assert dequeued is not None
    assert dequeued.job_id == job_id
    assert await queue.get_status(job_id) == JobStatus.PROCESSING

    await queue.ack(job_id)
    assert await queue.get_status(job_id) == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_nack_schedules_retry_and_promotes_back_to_stream():
    fake = _FakeRedis()
    queue = RedisJobQueue(
        redis_client=_FakeRedisClientWrapper(client=fake),
        consumer_name="test-consumer",
        retry_schedule_seconds=(0,),
    )

    job = JobPayload(
        job_type="meal_image_analysis",
        user_id="user-2",
        payload={"meal_id": "meal-2"},
    )
    await queue.enqueue(job)
    _ = await queue.dequeue(["meal_image_analysis"])

    await queue.nack(job.job_id, "temporary error")
    assert await queue.get_status(job.job_id) == JobStatus.FAILED

    # Dequeue will promote due retries first, then consume from stream.
    retry_job = await queue.dequeue(["meal_image_analysis"])
    assert retry_job is not None
    assert retry_job.job_id == job.job_id
    assert retry_job.retry_count == 1
    assert await queue.get_status(job.job_id) == JobStatus.PROCESSING


@pytest.mark.asyncio
async def test_nack_moves_job_to_dead_letter_after_max_retries():
    fake = _FakeRedis()
    queue = RedisJobQueue(
        redis_client=_FakeRedisClientWrapper(client=fake),
        consumer_name="test-consumer",
        retry_schedule_seconds=(0,),
    )

    job = JobPayload(
        job_type="meal_image_analysis",
        user_id="user-3",
        payload={"meal_id": "meal-3"},
        max_retries=1,
    )
    await queue.enqueue(job)

    # Failure #1 -> scheduled retry
    _ = await queue.dequeue(["meal_image_analysis"])
    await queue.nack(job.job_id, "first failure")
    assert await queue.get_status(job.job_id) == JobStatus.FAILED

    # Consume retry and fail again -> DEAD
    _ = await queue.dequeue(["meal_image_analysis"])
    await queue.nack(job.job_id, "second failure")
    assert await queue.get_status(job.job_id) == JobStatus.DEAD

    dead_entries = fake.streams["jobs:dead"]
    assert len(dead_entries) == 1
    _, dead_payload = dead_entries[0]
    assert dead_payload["job_id"] == job.job_id
    assert dead_payload["error"] == "second failure"

