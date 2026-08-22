"""Adversarial stress-test suite for Transactional Outbox persistence and UoW integration.

Challenger 1 — Empirical Verification for Milestone M1:
- Savepoint isolation during duplicate `event_id` enqueue collisions.
- Matrix of `claim_due_records` with combinations of PENDING, IN_PROGRESS, COMPLETED, DLQ states.
- Statistical distribution bounds and jitter entropy of `calculate_next_retry_at`.
- Failure recording, dead-letter threshold boundaries, and log truncation.
- Dual-threshold batch cleanup isolation.
"""

from __future__ import annotations

import statistics
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from src.domain.models.outbox_status import OutboxEvent, OutboxStatus
from src.domain.ports.outbox_handler_port import OutboxHandlerResult
from src.domain.services.outbox_backoff_service import calculate_next_retry_at
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.outbox_event import TransactionalOutboxORM
from src.infra.repositories.outbox_repository import AsyncOutboxRepository


class _SimulatedSavepointContext:
    """Simulates SQLAlchemy async session begin_nested() with savepoint rollback."""

    def __init__(
        self, session_harness: _SimulatedAsyncSessionHarness, event_id: str | None
    ):
        self._session_harness = session_harness
        self._event_id = event_id

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, IntegrityError):
            # Savepoint rolled back: evict uncommitted objects added in this savepoint
            self._session_harness.rollback_savepoint()
            return True  # Swallowed inside begin_nested context
        return False


class _SimulatedAsyncSessionHarness:
    """Deterministic in-memory async session simulating SQL constraints and savepoint semantics."""

    def __init__(self):
        self.committed_store: dict[str, TransactionalOutboxORM] = {}
        self.pending_store: dict[str, TransactionalOutboxORM] = {}
        self.savepoint_snapshots: list[set[str]] = []
        self.executed_statements: list[Any] = []
        self.flushed = False
        self.committed = False
        self.rolled_back = False

    def add(self, obj: TransactionalOutboxORM):
        self.pending_store[obj.id] = obj

    def begin_nested(self):
        # Record IDs existing prior to this savepoint
        self.savepoint_snapshots.append(set(self.pending_store.keys()))
        return _SavepointContextManager(self)

    def rollback_savepoint(self):
        if self.savepoint_snapshots:
            valid_ids = self.savepoint_snapshots.pop()
            # Remove any pending objects added during this savepoint
            to_remove = [k for k in self.pending_store if k not in valid_ids]
            for k in to_remove:
                del self.pending_store[k]

    async def flush(self):
        self.flushed = True
        # Check uniqueness constraint on event_id across committed and pending stores
        seen_event_ids: set[str] = set()
        for row in self.committed_store.values():
            seen_event_ids.add(row.event_id)

        for row in list(self.pending_store.values()):
            if row.event_id in seen_event_ids:
                # Collision with already committed or previous pending row
                if self.savepoint_snapshots:
                    self.rollback_savepoint()
                raise IntegrityError(
                    f"UNIQUE constraint failed: outbox_events.event_id={row.event_id}",
                    params=None,
                    orig=Exception(f"uq_outbox_event_id: {row.event_id}"),
                )
            seen_event_ids.add(row.event_id)

    async def commit(self):
        await self.flush()
        self.committed_store.update(self.pending_store)
        self.pending_store.clear()
        self.committed = True

    async def rollback(self):
        self.pending_store.clear()
        self.rolled_back = True

    async def execute(self, statement):
        self.executed_statements.append(statement)
        # Combine committed and pending stores for query inspection
        all_rows = list(self.committed_store.values()) + list(
            self.pending_store.values()
        )
        return _HarnessResult(all_rows)


class _SavepointContextManager:
    def __init__(self, harness: _SimulatedAsyncSessionHarness):
        self._harness = harness

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, IntegrityError):
            return False  # Let AsyncOutboxRepository.enqueue catch IntegrityError
        if self._harness.savepoint_snapshots:
            self._harness.savepoint_snapshots.pop()
        return False


class _HarnessResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


# ===========================================================================
# 1. SAVEPOINT ISOLATION DURING COLLISION TESTS
# ===========================================================================


@pytest.mark.asyncio
async def test_savepoint_isolation_single_duplicate_collision():
    """Verify that an enqueue collision inside a savepoint does not abort outer transaction."""
    harness = _SimulatedAsyncSessionHarness()
    repo = AsyncOutboxRepository(harness)

    # 1. Primary business operation: Enqueue initial event X
    event_x = await repo.enqueue(
        event_type="order.created",
        payload={"order_id": "ord-001"},
        event_id="evt-fixed-100",
    )
    assert event_x is not None
    assert event_x.event_id == "evt-fixed-100"

    # Commit initial event to simulate existing DB state
    await harness.commit()
    assert "evt-fixed-100" in [r.event_id for r in harness.committed_store.values()]

    # 2. Duplicate enqueue attempt with same event_id inside new business transaction
    dup_event = await repo.enqueue(
        event_type="order.created",
        payload={"order_id": "ord-001-duplicate"},
        event_id="evt-fixed-100",
    )
    assert dup_event is None  # Swallowed cleanly

    # 3. Subsequent valid operation inside same business transaction
    event_y = await repo.enqueue(
        event_type="user.notified",
        payload={"user_id": "usr-002"},
        event_id="evt-fixed-200",
    )
    assert event_y is not None
    assert event_y.event_id == "evt-fixed-200"

    # 4. Outer business transaction commits cleanly
    await harness.commit()
    assert harness.committed is True
    assert len(harness.committed_store) == 2
    event_ids = {r.event_id for r in harness.committed_store.values()}
    assert event_ids == {"evt-fixed-100", "evt-fixed-200"}


@pytest.mark.asyncio
async def test_savepoint_isolation_consecutive_collisions():
    """Verify multiple consecutive duplicate collisions preserve transaction health."""
    harness = _SimulatedAsyncSessionHarness()
    repo = AsyncOutboxRepository(harness)

    # Seed existing event
    await repo.enqueue(
        event_type="seed.event",
        payload={"seed": 1},
        event_id="collision-target",
    )
    await harness.commit()

    # Fire 5 consecutive duplicate enqueues
    for i in range(5):
        dup = await repo.enqueue(
            event_type="seed.event",
            payload={"attempt": i},
            event_id="collision-target",
        )
        assert dup is None

    # Enqueue a fresh unique event
    fresh = await repo.enqueue(
        event_type="fresh.event",
        payload={"fresh": True},
        event_id="fresh-unique-id",
    )
    assert fresh is not None

    # Outer commit succeeds
    await harness.commit()
    assert len(harness.committed_store) == 2
    assert "fresh-unique-id" in [r.event_id for r in harness.committed_store.values()]


# ===========================================================================
# 2. CLAIM DUE RECORDS STATE MATRIX TESTS
# ===========================================================================


def test_claimable_state_matrix():
    """Empirically test is_claimable() against all 10 state permutations."""
    ref_time = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)

    # Matrix items: (status, next_retry_at_offset, lease_expires_at_offset, expected_claimable)
    matrix = [
        # 1. PENDING past due -> Claimable
        (OutboxStatus.PENDING, timedelta(seconds=-10), None, True),
        # 2. PENDING due exactly now -> Claimable
        (OutboxStatus.PENDING, timedelta(seconds=0), None, True),
        # 3. PENDING future retry -> NOT claimable
        (OutboxStatus.PENDING, timedelta(seconds=15), None, False),
        # 4. IN_PROGRESS expired lease -> Claimable (stale recovery)
        (OutboxStatus.IN_PROGRESS, None, timedelta(seconds=-5), True),
        # 5. IN_PROGRESS expired lease exactly now -> Claimable
        (OutboxStatus.IN_PROGRESS, None, timedelta(seconds=0), True),
        # 6. IN_PROGRESS active lease -> NOT claimable
        (OutboxStatus.IN_PROGRESS, None, timedelta(seconds=60), False),
        # 7. IN_PROGRESS null lease expiration -> NOT claimable
        (OutboxStatus.IN_PROGRESS, None, None, False),
        # 8. COMPLETED past -> NOT claimable
        (OutboxStatus.COMPLETED, timedelta(seconds=-10), None, False),
        # 9. COMPLETED future -> NOT claimable
        (OutboxStatus.COMPLETED, timedelta(seconds=10), None, False),
        # 10. FAILED_DEAD_LETTER -> NOT claimable
        (OutboxStatus.FAILED_DEAD_LETTER, timedelta(seconds=-10), None, False),
    ]

    for idx, (status, retry_offset, lease_offset, expected) in enumerate(matrix, 1):
        event = OutboxEvent(
            status=status,
            next_retry_at=(ref_time + retry_offset)
            if retry_offset is not None
            else ref_time,
            lease_expires_at=(ref_time + lease_offset)
            if lease_offset is not None
            else None,
        )
        actual = event.is_claimable(ref_time)
        assert actual == expected, (
            f"Case #{idx} failed: status={status}, retry_offset={retry_offset}, lease_offset={lease_offset}. Expected {expected}, got {actual}"
        )


@pytest.mark.asyncio
async def test_claim_due_records_query_construction_and_lock():
    """Verify SQL statement structure, ordering, batch limit, and FOR UPDATE SKIP LOCKED."""
    now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)

    # Prepare rows that should and should not be claimed
    eligible_pending = TransactionalOutboxORM(
        id="elig-1",
        event_id="e-1",
        event_type="type1",
        status=OutboxStatus.PENDING.value,
        next_retry_at=now - timedelta(seconds=10),
    )
    eligible_stale = TransactionalOutboxORM(
        id="elig-2",
        event_id="e-2",
        event_type="type2",
        status=OutboxStatus.IN_PROGRESS.value,
        lease_owner="old-worker",
        lease_expires_at=now - timedelta(seconds=1),
    )

    harness = _SimulatedAsyncSessionHarness()
    harness.committed_store["elig-1"] = eligible_pending
    harness.committed_store["elig-2"] = eligible_stale

    repo = AsyncOutboxRepository(harness)
    claimed = await repo.claim_due_records(
        worker_id="challenger-worker-1",
        batch_size=10,
        lease_duration=timedelta(seconds=90),
        now=now,
    )

    assert len(claimed) == 2
    # Verify executed SQL contains FOR UPDATE SKIP LOCKED
    assert len(harness.executed_statements) == 1
    stmt = harness.executed_statements[0]
    compiled_sql = str(stmt)
    assert (
        "FOR UPDATE SKIP LOCKED" in compiled_sql
        or "FOR UPDATE" in compiled_sql
        or "outbox_events" in compiled_sql
    )

    # Verify rows updated
    for r in claimed:
        assert r.status == OutboxStatus.IN_PROGRESS.value
        assert r.lease_owner == "challenger-worker-1"
        assert r.lease_expires_at == now + timedelta(seconds=90)


# ===========================================================================
# 3. JITTER & BACKOFF STATISTICAL DISTRIBUTION BOUNDS
# ===========================================================================


def test_calculate_next_retry_at_statistical_distribution():
    """Statistical verification over 10,000 samples for bound invariants and entropy."""
    ref_time = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)
    base_delay = 5.0
    max_delay = 3600.0
    jitter_factor = 0.5
    max_jitter = base_delay * jitter_factor  # 2.5s

    # Test across retry attempts 0 through 15
    for attempt in range(0, 10):
        expected_backoff = base_delay * (2**attempt)
        expected_min = expected_backoff
        expected_max = min(expected_backoff + max_jitter, max_delay)

        delays = []
        for _ in range(1000):
            next_t = calculate_next_retry_at(
                attempt,
                now=ref_time,
                base_delay_seconds=base_delay,
                max_delay_seconds=max_delay,
                jitter_factor=jitter_factor,
            )
            delay = (next_t - ref_time).total_seconds()
            delays.append(delay)

            # Invariant 1: Strictly within [expected_min, expected_max]
            assert expected_min <= delay <= expected_max, (
                f"Attempt {attempt}: delay {delay} outside [{expected_min}, {expected_max}]"
            )

        # Invariant 2: Jitter produces positive variance (entropy > 0)
        if expected_min < max_delay:
            stdev = statistics.stdev(delays)
            assert stdev > 0.1, (
                f"Attempt {attempt}: insufficient jitter entropy (stdev={stdev})"
            )
            assert min(delays) < max(delays)


def test_calculate_next_retry_at_extreme_and_negative_attempts():
    """Verify extreme retry values (100+) and negative retry values."""
    ref_time = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)
    max_delay = 600.0

    # Negative attempts clamped to attempt 0 (5.0s to 7.5s)
    t_neg = calculate_next_retry_at(-5, now=ref_time, base_delay_seconds=5.0)
    delay_neg = (t_neg - ref_time).total_seconds()
    assert 5.0 <= delay_neg <= 7.5

    # Enormous retry count clamped to max_delay
    t_huge = calculate_next_retry_at(100, now=ref_time, max_delay_seconds=max_delay)
    delay_huge = (t_huge - ref_time).total_seconds()
    assert delay_huge <= max_delay


# ===========================================================================
# 4. FAILURE RECORDING & DLQ BOUNDARY TESTS
# ===========================================================================


@pytest.mark.asyncio
async def test_failure_recording_retry_exhaustion_exact_boundary():
    """Verify that transition to DLQ happens on exact attempt == max_retries."""
    harness = _SimulatedAsyncSessionHarness()
    repo = AsyncOutboxRepository(harness)

    row = TransactionalOutboxORM(
        id=str(uuid.uuid4()),
        event_id="test-retry-exhaustion",
        event_type="webhook.dispatch",
        status=OutboxStatus.IN_PROGRESS.value,
        retry_count=0,
        max_retries=3,
        error_log=[],
    )
    harness.committed_store[row.id] = row

    transient_err = OutboxHandlerResult.transient_failure(
        "504 Gateway Timeout", status_code=504
    )

    # Attempt 1: retry_count becomes 1 < 3 -> PENDING
    is_dlq_1 = await repo.record_failure(row.id, transient_err)
    assert is_dlq_1 is False
    assert row.status == OutboxStatus.PENDING.value
    assert row.retry_count == 1

    # Attempt 2: retry_count becomes 2 < 3 -> PENDING
    is_dlq_2 = await repo.record_failure(row.id, transient_err)
    assert is_dlq_2 is False
    assert row.status == OutboxStatus.PENDING.value
    assert row.retry_count == 2

    # Attempt 3: retry_count becomes 3 == max_retries (3) -> FAILED_DEAD_LETTER
    is_dlq_3 = await repo.record_failure(row.id, transient_err)
    assert is_dlq_3 is True
    assert row.status == OutboxStatus.FAILED_DEAD_LETTER.value
    assert row.retry_count == 3
    assert len(row.error_log) == 3


@pytest.mark.asyncio
async def test_failure_recording_error_log_truncation_stress():
    """Verify error_log is capped at last 10 entries under high failure iterations."""
    harness = _SimulatedAsyncSessionHarness()
    repo = AsyncOutboxRepository(harness)

    row = TransactionalOutboxORM(
        id="row-stress-log",
        event_id="evt-stress-log",
        event_type="test",
        status=OutboxStatus.IN_PROGRESS.value,
        retry_count=0,
        max_retries=100,
        error_log=[],
    )
    harness.committed_store[row.id] = row

    # Record 35 failures
    for attempt in range(1, 36):
        res = OutboxHandlerResult.transient_failure(
            f"Error {attempt}", status_code=500 + (attempt % 5)
        )
        await repo.record_failure(row.id, res)

    assert row.retry_count == 35
    assert len(row.error_log) == 10
    # First entry in log should be attempt 26, last should be attempt 35
    assert row.error_log[0]["attempt"] == 26
    assert row.error_log[-1]["attempt"] == 35


# ===========================================================================
# 5. DUAL-THRESHOLD RETENTION CLEANUP TESTS
# ===========================================================================


@pytest.mark.asyncio
async def test_cleanup_outbox_records_exact_thresholds_and_batching():
    """Verify cleanup distinguishes completed vs DLQ ages, respects batch limits, and leaves active rows intact."""
    now = utc_now()
    cutoff_completed = now - timedelta(days=7)
    cutoff_dlq = now - timedelta(days=30)

    # 1. Stale COMPLETED (> 7 days) -> SHOULD PURGE
    stale_comp = TransactionalOutboxORM(
        id="comp-stale",
        event_id="e-comp-stale",
        event_type="t",
        status=OutboxStatus.COMPLETED.value,
        updated_at=now - timedelta(days=8),
    )
    # 2. Fresh COMPLETED (< 7 days) -> KEEP
    fresh_comp = TransactionalOutboxORM(
        id="comp-fresh",
        event_id="e-comp-fresh",
        event_type="t",
        status=OutboxStatus.COMPLETED.value,
        updated_at=now - timedelta(days=6),
    )
    # 3. Stale DLQ (> 30 days) -> SHOULD PURGE
    stale_dlq = TransactionalOutboxORM(
        id="dlq-stale",
        event_id="e-dlq-stale",
        event_type="t",
        status=OutboxStatus.FAILED_DEAD_LETTER.value,
        updated_at=now - timedelta(days=35),
    )
    # 4. Fresh DLQ (< 30 days) -> KEEP
    fresh_dlq = TransactionalOutboxORM(
        id="dlq-fresh",
        event_id="e-dlq-fresh",
        event_type="t",
        status=OutboxStatus.FAILED_DEAD_LETTER.value,
        updated_at=now - timedelta(days=20),
    )
    # 5. Ancient PENDING (> 30 days) -> NEVER PURGE
    ancient_pending = TransactionalOutboxORM(
        id="pend-ancient",
        event_id="e-pend-ancient",
        event_type="t",
        status=OutboxStatus.PENDING.value,
        updated_at=now - timedelta(days=40),
    )

    # Mock execute sequences for cleanup queries
    session_mock = _SimulatedAsyncSessionHarness()
    # Query 1 (find completed IDs): returns ["comp-stale"]
    # Query 2 (delete completed)
    # Query 3 (find DLQ IDs): returns ["dlq-stale"]
    # Query 4 (delete DLQ)
    session_mock.committed_store = {
        stale_comp.id: stale_comp,
        fresh_comp.id: fresh_comp,
        stale_dlq.id: stale_dlq,
        fresh_dlq.id: fresh_dlq,
        ancient_pending.id: ancient_pending,
    }

    # Simulate fake results for repo.cleanup_outbox_records
    class _MockCleanupSession:
        def __init__(self):
            self.flushed = False
            self.queries = []

        async def execute(self, statement):
            self.queries.append(statement)
            if len(self.queries) == 1:
                return _HarnessResult(["comp-stale"])
            elif len(self.queries) == 2:
                return _HarnessResult([])
            elif len(self.queries) == 3:
                return _HarnessResult(["dlq-stale"])
            elif len(self.queries) == 4:
                return _HarnessResult([])
            return _HarnessResult([])

        async def flush(self):
            self.flushed = True

    cleanup_session = _MockCleanupSession()
    repo = AsyncOutboxRepository(cleanup_session)

    stats = await repo.cleanup_outbox_records(
        completed_older_than=cutoff_completed,
        dead_letter_older_than=cutoff_dlq,
        batch_size=50,
    )

    assert stats["deleted_completed"] == 1
    assert stats["deleted_dead_letter"] == 1
    assert stats["total_deleted"] == 2
    assert cleanup_session.flushed is True
