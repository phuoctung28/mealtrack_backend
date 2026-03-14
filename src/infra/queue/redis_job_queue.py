"""
Redis Streams implementation of JobQueuePort.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from redis.exceptions import RedisError, ResponseError

from src.domain.model.job_queue import JobPayload, JobStatus
from src.domain.ports.job_queue_port import JobQueuePort
from src.infra.cache.redis_client import RedisClient

logger = logging.getLogger(__name__)


class RedisJobQueue(JobQueuePort):
    """Queue implementation backed by Redis Streams + consumer groups."""

    def __init__(
        self,
        redis_client: RedisClient,
        stream_name: str = "jobs:stream",
        dead_letter_stream: str = "jobs:dead",
        consumer_group: str = "jobs:workers",
        consumer_name: Optional[str] = None,
        max_retries: int = 3,
        retry_schedule_seconds: tuple[int, ...] = (5, 15),
    ):
        self._redis = redis_client
        self._stream_name = stream_name
        self._dead_letter_stream = dead_letter_stream
        self._consumer_group = consumer_group
        self._consumer_name = consumer_name or f"consumer-{uuid4()}"
        self._max_retries = max_retries
        self._retry_schedule_seconds = retry_schedule_seconds
        self._retry_zset = f"{stream_name}:retry_schedule"
        self._group_initialized = False

    async def enqueue(self, payload: JobPayload) -> str:
        client = self._require_client()
        await self._ensure_group()

        payload.max_retries = payload.max_retries or self._max_retries

        fields = self._serialize_payload(payload)
        await client.xadd(self._stream_name, fields)
        await self._set_job_state(
            payload,
            status=JobStatus.QUEUED,
            extra={"queued_at": self._utc_now_iso()},
        )
        await self._increment_metric("jobs_enqueued_total")
        return payload.job_id

    async def dequeue(
        self, job_types: list[str], block_ms: int = 5000
    ) -> Optional[JobPayload]:
        del job_types  # Router-level filtering will be handled by worker layer.

        client = self._require_client()
        await self._ensure_group()
        await self._promote_due_retries()

        response = await client.xreadgroup(
            groupname=self._consumer_group,
            consumername=self._consumer_name,
            streams={self._stream_name: ">"},
            count=1,
            block=block_ms,
        )
        if not response:
            return None

        stream_entries = response[0][1]
        stream_id, fields = stream_entries[0]
        payload = self._deserialize_payload(fields)
        await self._set_job_state(
            payload,
            status=JobStatus.PROCESSING,
            extra={
                "stream_id": stream_id,
                "started_at": self._utc_now_iso(),
                "consumer_name": self._consumer_name,
            },
        )
        return payload

    async def ack(self, job_id: str) -> None:
        client = self._require_client()

        state = await client.hgetall(self._job_state_key(job_id))
        stream_id = state.get("stream_id")

        if stream_id:
            await client.xack(self._stream_name, self._consumer_group, stream_id)
            await client.xdel(self._stream_name, stream_id)

        payload = self._payload_from_state(job_id, state)
        await self._set_job_state(
            payload,
            status=JobStatus.COMPLETED,
            extra={"completed_at": self._utc_now_iso()},
        )
        await client.zrem(self._retry_zset, job_id)

    async def nack(self, job_id: str, error: str) -> None:
        client = self._require_client()
        state = await client.hgetall(self._job_state_key(job_id))
        if not state:
            return

        payload = self._payload_from_state(job_id, state)
        payload.retry_count += 1

        stream_id = state.get("stream_id")
        if stream_id:
            await client.xack(self._stream_name, self._consumer_group, stream_id)
            await client.xdel(self._stream_name, stream_id)

        if payload.retry_count > payload.max_retries:
            await self._move_to_dead_letter(payload, error)
            await self._set_job_state(
                payload,
                status=JobStatus.DEAD,
                extra={
                    "failed_at": self._utc_now_iso(),
                    "last_error": error,
                },
            )
            await self._increment_metric("jobs_dead_total")
            return

        delay = self._retry_delay_seconds(payload.retry_count)
        due_at_epoch = time.time() + delay

        await self._set_job_state(
            payload,
            status=JobStatus.FAILED,
            extra={
                "failed_at": self._utc_now_iso(),
                "last_error": error,
                "retry_count": str(payload.retry_count),
                "next_retry_at_epoch": str(due_at_epoch),
            },
        )

        await client.zadd(self._retry_zset, {job_id: due_at_epoch})
        await self._increment_metric("jobs_nacked_total")

    async def get_status(self, job_id: str) -> Optional[JobStatus]:
        client = self._require_client()
        state = await client.hgetall(self._job_state_key(job_id))
        if not state:
            return None
        value = state.get("status")
        if not value:
            return None
        return JobStatus(value)

    async def _ensure_group(self) -> None:
        if self._group_initialized:
            return

        client = self._require_client()
        try:
            await client.xgroup_create(
                name=self._stream_name,
                groupname=self._consumer_group,
                id="$",
                mkstream=True,
            )
            logger.info(
                "Created Redis stream group '%s' on '%s'",
                self._consumer_group,
                self._stream_name,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        self._group_initialized = True

    async def _promote_due_retries(self) -> None:
        client = self._require_client()
        now = time.time()

        while True:
            # Atomically pop the job with the smallest retry timestamp.
            items = await client.zpopmin(self._retry_zset, 1)
            if not items:
                # No more jobs in the retry set.
                break

            job_id, score = items[0]

            # If the earliest job is not yet due, put it back and stop.
            if score > now:
                await client.zadd(self._retry_zset, {job_id: score})
                break

            state = await client.hgetall(self._job_state_key(job_id))
            if not state:
                # Job state no longer exists; nothing to re-enqueue.
                continue

            payload = self._payload_from_state(job_id, state)
            await client.xadd(self._stream_name, self._serialize_payload(payload))
            await self._set_job_state(
                payload,
                status=JobStatus.QUEUED,
                extra={
                    "queued_at": self._utc_now_iso(),
                    "stream_id": "",
                },
            )

    async def _set_job_state(
        self,
        payload: JobPayload,
        status: JobStatus,
        extra: Optional[dict[str, str]] = None,
    ) -> None:
        client = self._require_client()

        state: dict[str, str] = {
            "job_id": payload.job_id,
            "job_type": payload.job_type,
            "user_id": payload.user_id,
            "status": status.value,
            "priority": str(payload.priority),
            "max_retries": str(payload.max_retries),
            "retry_count": str(payload.retry_count),
            "created_at": payload.created_at.isoformat(),
            "payload_json": json.dumps(payload.payload),
            "updated_at": self._utc_now_iso(),
        }
        if extra:
            state.update(extra)

        await client.hset(self._job_state_key(payload.job_id), mapping=state)

    async def _move_to_dead_letter(self, payload: JobPayload, error: str) -> None:
        client = self._require_client()
        fields = self._serialize_payload(payload)
        fields["error"] = error
        fields["dead_at"] = self._utc_now_iso()
        await client.xadd(self._dead_letter_stream, fields)

    async def _increment_metric(self, metric_name: str) -> None:
        try:
            client = self._require_client()
            await client.incr(f"metrics:{metric_name}")
        except RedisError:
            logger.debug("Could not increment metric '%s'", metric_name, exc_info=True)

    def _serialize_payload(self, payload: JobPayload) -> dict[str, str]:
        return {
            "job_id": payload.job_id,
            "job_type": payload.job_type,
            "user_id": payload.user_id,
            "created_at": payload.created_at.isoformat(),
            "priority": str(payload.priority),
            "max_retries": str(payload.max_retries),
            "retry_count": str(payload.retry_count),
            "payload_json": json.dumps(payload.payload),
        }

    def _deserialize_payload(self, fields: dict[str, Any]) -> JobPayload:
        created_at_raw = fields.get("created_at")
        if created_at_raw:
            created_at = datetime.fromisoformat(created_at_raw)
        else:
            created_at = datetime.now(timezone.utc)

        return JobPayload(
            job_id=fields["job_id"],
            job_type=fields["job_type"],
            user_id=fields["user_id"],
            created_at=created_at,
            priority=int(fields.get("priority", 0)),
            max_retries=int(fields.get("max_retries", self._max_retries)),
            retry_count=int(fields.get("retry_count", 0)),
            payload=json.loads(fields.get("payload_json", "{}")),
        )

    def _payload_from_state(self, job_id: str, state: dict[str, str]) -> JobPayload:
        created_at = datetime.fromisoformat(state["created_at"])
        payload_json = json.loads(state.get("payload_json", "{}"))
        return JobPayload(
            job_id=job_id,
            job_type=state["job_type"],
            user_id=state["user_id"],
            payload=payload_json,
            priority=int(state.get("priority", 0)),
            max_retries=int(state.get("max_retries", self._max_retries)),
            retry_count=int(state.get("retry_count", 0)),
            created_at=created_at,
        )

    def _retry_delay_seconds(self, retry_count: int) -> int:
        if retry_count <= 0:
            return 0
        if retry_count <= len(self._retry_schedule_seconds):
            return self._retry_schedule_seconds[retry_count - 1]
        return self._retry_schedule_seconds[-1]

    def _job_state_key(self, job_id: str) -> str:
        return f"jobs:state:{job_id}"

    def _require_client(self):
        client = self._redis.client
        if client is None:
            raise RuntimeError("Redis client is not connected")
        return client

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

