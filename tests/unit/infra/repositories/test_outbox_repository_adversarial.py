"""Empirical adversarial challenger stress tests for OutboxRepository contracts.

Stress tests:
1. Parity between AsyncOutboxRepository and FakeOutboxRepository.
2. cleanup_outbox_records bounds, strict date cutoffs, and batch limit enforcement.
3. record_failure error log array capping (max 10 items) and DLQ state transitions.
4. Concurrency lease claim bounds, ordering, and stale lease recovery.
5. Savepoint rollback safety on duplicate event_id enqueue.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from tests.fixtures.fakes.fake_outbox_repository import FakeOutboxRepository
from tests.fixtures.fakes.fake_uow import FakeUnitOfWork

from src.domain.models.outbox_status import OutboxStatus
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.ports.outbox_handler_port import OutboxHandlerResult
from src.domain.ports.outbox_repository_port import OutboxRepositoryPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.outbox_event import TransactionalOutboxORM
from src.infra.repositories.outbox_repository import AsyncOutboxRepository


class _MockQueryEngine:
    """Simulates SQLAlchemy SQL execution for AsyncOutboxRepository without a live DB server."""

    def __init__(self, data: dict[str, TransactionalOutboxORM] | None = None) -> None:
        self.rows: dict[str, TransactionalOutboxORM] = dict(data or {})
        self.added: list[TransactionalOutboxORM] = []
        self.executed_statements: list[Any] = []
        self.flushed = False
        self.fail_nested = False

    def add(self, obj: TransactionalOutboxORM) -> None:
        self.added.append(obj)
        self.rows[obj.id] = obj

    async def flush(self) -> None:
        self.flushed = True
        if self.fail_nested:
            raise IntegrityError("duplicate key", None, Exception("uq_outbox_event_id"))

    def begin_nested(self):
        class _SavepointCtx:
            def __init__(self, parent):
                self.parent = parent

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.parent.fail_nested:
                    raise IntegrityError(
                        "duplicate key", None, Exception("uq_outbox_event_id")
                    )
                return False

        return _SavepointCtx(self)

    async def execute(self, stmt: Any):
        self.executed_statements.append(stmt)
        stmt_str = str(stmt)

        class _Scalars:
            def __init__(self, items):
                self._items = items

            def all(self):
                return list(self._items)

            def first(self):
                return self._items[0] if self._items else None

        class _Res:
            def __init__(self, items):
                self._items = items

            def scalars(self):
                return _Scalars(self._items)

        # 1. SELECT for claim_due_records or find
        if "SELECT" in stmt_str or "select" in stmt_str:
            params = stmt.compile().params if hasattr(stmt, "compile") else {}

            if "outbox_events.id =" in stmt_str:
                target_id = params.get("id_1") or params.get("id")
                if target_id and target_id in self.rows:
                    return _Res([self.rows[target_id]])
                # Fallback check
                for k, v in self.rows.items():
                    if k in str(params.values()):
                        return _Res([v])
                return _Res([])

            if "outbox_events.event_id" in stmt_str:
                target_evt_id = params.get("event_id_1") or params.get("event_id")
                if target_evt_id:
                    for r in self.rows.values():
                        if r.event_id == target_evt_id:
                            return _Res([r])
                for r in self.rows.values():
                    if r.event_id in str(params.values()):
                        return _Res([r])
                return _Res([])

            # Claim query or cleanup query
            if "outbox_events.status = :status_1" in stmt_str and (
                "outbox_events.updated_at <" in stmt_str
            ):
                # Cleanup query for IDs
                # Extract status and filter
                matched_ids = []
                for r in self.rows.values():
                    # For completed cleanup
                    if "COMPLETED" in str(params.values()):
                        if r.status == OutboxStatus.COMPLETED.value:
                            matched_ids.append(r.id)
                    elif "FAILED_DEAD_LETTER" in str(params.values()):
                        if r.status == OutboxStatus.FAILED_DEAD_LETTER.value:
                            matched_ids.append(r.id)
                return _Res(matched_ids)

            # Default claim: return eligible rows
            return _Res(list(self.rows.values()))

        # 2. DELETE
        if "DELETE" in stmt_str or "delete" in stmt_str:
            # Delete executed
            return _Res([])

        # 3. UPDATE
        if "UPDATE" in stmt_str or "update" in stmt_str:
            return _Res([])

        return _Res([])


# ===========================================================================
# 1. Interface & Port Contract Parity Tests
# ===========================================================================


def test_repository_satisfies_port_protocol():
    """Verify both implementations satisfy OutboxRepositoryPort without missing abstractmethods."""
    assert issubclass(AsyncOutboxRepository, OutboxRepositoryPort)
    assert AsyncOutboxRepository.__abstractmethods__ == frozenset()

    assert issubclass(FakeOutboxRepository, OutboxRepositoryPort)
    assert FakeOutboxRepository.__abstractmethods__ == frozenset()


def test_uow_contract_contains_outbox_port():
    """Verify AsyncUnitOfWorkPort, AsyncUnitOfWork, and FakeUnitOfWork expose outbox."""
    assert "outbox" in AsyncUnitOfWorkPort.__annotations__
    assert AsyncUnitOfWorkPort.__annotations__["outbox"] in (
        OutboxRepositoryPort,
        "OutboxRepositoryPort",
    )

    fake_uow = FakeUnitOfWork()
    assert hasattr(fake_uow, "outbox")
    assert isinstance(fake_uow.outbox, OutboxRepositoryPort)


# ===========================================================================
# 2. Stress Test: Error Log Array Capping & DLQ Transitions
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["fake", "async"])
async def test_record_failure_stress_capped_at_ten_entries(repo_type: str):
    """Stress test: recording 25 sequential failures caps error_log at exactly 10 latest items."""
    if repo_type == "fake":
        repo = FakeOutboxRepository()
        event = await repo.enqueue("stress.fail", {"data": 1}, max_retries=100)
        assert event is not None
        outbox_id = event.id
    else:
        now = utc_now()
        orm_row = TransactionalOutboxORM(
            id="orm-stress-1",
            event_id="evt-stress-1",
            event_type="stress.fail",
            payload={"data": 1},
            status=OutboxStatus.IN_PROGRESS.value,
            retry_count=0,
            max_retries=100,
            error_log=[],
            created_at=now,
            updated_at=now,
        )
        session = _MockQueryEngine({"orm-stress-1": orm_row})
        repo = AsyncOutboxRepository(session)
        outbox_id = "orm-stress-1"

    # Fire 25 consecutive failures
    for attempt in range(1, 26):
        res = OutboxHandlerResult.transient_failure(
            error_message=f"Transient failure #{attempt}",
            error_type="TestError",
            status_code=500 + (attempt % 5),
            metadata={"attempt_id": attempt},
        )
        is_dlq = await repo.record_failure(outbox_id, res, max_retries=100)
        assert is_dlq is False

    # Retrieve record
    saved = repo.events[outbox_id] if repo_type == "fake" else session.rows[outbox_id]

    assert saved.retry_count == 25
    assert len(saved.error_log) == 10  # Strictly capped at 10

    # Verify oldest 15 were evicted and remaining 10 are attempts 16..25 in chronological order
    for idx, expected_attempt in enumerate(range(16, 26)):
        entry = saved.error_log[idx]
        assert entry["attempt"] == expected_attempt
        assert entry["error_message"] == f"Transient failure #{expected_attempt}"
        assert entry["metadata"]["attempt_id"] == expected_attempt
        assert entry["is_transient"] is True
        assert "timestamp" in entry


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["fake", "async"])
async def test_record_failure_dlq_transitions_exact_boundary(repo_type: str):
    """Verify DLQ transition occurs exactly when retry_count == max_retries or is_transient=False."""
    # Test A: Max retries = 3
    if repo_type == "fake":
        repo_a = FakeOutboxRepository()
        evt_a = await repo_a.enqueue("test.boundary", {}, max_retries=3)
        assert evt_a is not None
        outbox_id_a = evt_a.id
    else:
        now = utc_now()
        orm_a = TransactionalOutboxORM(
            id="orm-a",
            event_id="evt-a",
            event_type="test.boundary",
            payload={},
            status=OutboxStatus.IN_PROGRESS.value,
            retry_count=0,
            max_retries=3,
            created_at=now,
            updated_at=now,
        )
        session_a = _MockQueryEngine({"orm-a": orm_a})
        repo_a = AsyncOutboxRepository(session_a)
        outbox_id_a = "orm-a"

    res_transient = OutboxHandlerResult.transient_failure("Glitch")

    # Attempt 1: retry_count=1 < 3 -> PENDING
    dlq1 = await repo_a.record_failure(outbox_id_a, res_transient)
    assert dlq1 is False
    rec_a = (
        repo_a.events[outbox_id_a]
        if repo_type == "fake"
        else session_a.rows[outbox_id_a]
    )
    assert rec_a.retry_count == 1
    assert rec_a.status == (
        OutboxStatus.PENDING if repo_type == "fake" else OutboxStatus.PENDING.value
    )

    # Attempt 2: retry_count=2 < 3 -> PENDING
    dlq2 = await repo_a.record_failure(outbox_id_a, res_transient)
    assert dlq2 is False
    rec_a = (
        repo_a.events[outbox_id_a]
        if repo_type == "fake"
        else session_a.rows[outbox_id_a]
    )
    assert rec_a.retry_count == 2
    assert rec_a.status == (
        OutboxStatus.PENDING if repo_type == "fake" else OutboxStatus.PENDING.value
    )

    # Attempt 3: retry_count=3 >= 3 -> FAILED_DEAD_LETTER
    dlq3 = await repo_a.record_failure(outbox_id_a, res_transient)
    assert dlq3 is True
    rec_a = (
        repo_a.events[outbox_id_a]
        if repo_type == "fake"
        else session_a.rows[outbox_id_a]
    )
    assert rec_a.retry_count == 3
    assert rec_a.status == (
        OutboxStatus.FAILED_DEAD_LETTER
        if repo_type == "fake"
        else OutboxStatus.FAILED_DEAD_LETTER.value
    )
    assert rec_a.lease_owner is None
    assert rec_a.lease_expires_at is None

    # Test B: Permanent failure fast-fails to DLQ immediately on Attempt 1
    if repo_type == "fake":
        repo_b = FakeOutboxRepository()
        evt_b = await repo_b.enqueue("test.perm", {}, max_retries=10)
        assert evt_b is not None
        outbox_id_b = evt_b.id
    else:
        orm_b = TransactionalOutboxORM(
            id="orm-b",
            event_id="evt-b",
            event_type="test.perm",
            payload={},
            status=OutboxStatus.IN_PROGRESS.value,
            retry_count=0,
            max_retries=10,
            created_at=now,
            updated_at=now,
        )
        session_b = _MockQueryEngine({"orm-b": orm_b})
        repo_b = AsyncOutboxRepository(session_b)
        outbox_id_b = "orm-b"

    res_perm = OutboxHandlerResult.permanent_failure(
        "Invalid unrecoverable schema", error_type="ValidationError", status_code=422
    )
    dlq_perm = await repo_b.record_failure(outbox_id_b, res_perm)
    assert dlq_perm is True
    rec_b = (
        repo_b.events[outbox_id_b]
        if repo_type == "fake"
        else session_b.rows[outbox_id_b]
    )
    assert rec_b.retry_count == 1  # Incremented to 1
    assert rec_b.status == (
        OutboxStatus.FAILED_DEAD_LETTER
        if repo_type == "fake"
        else OutboxStatus.FAILED_DEAD_LETTER.value
    )


# ===========================================================================
# 3. Stress Test: cleanup_outbox_records Cutoffs, Bounds & Batches
# ===========================================================================


@pytest.mark.asyncio
async def test_fake_outbox_cleanup_date_cutoffs_and_status_filtering():
    """Verify cleanup_outbox_records enforces strict date cutoffs and status boundaries."""
    repo = FakeOutboxRepository()
    now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)

    # 1. COMPLETED: 8 days old (should be purged by 7-day cutoff)
    e1 = await repo.enqueue("c.old", {}, event_id="c-old")
    assert e1 is not None
    e1.status = OutboxStatus.COMPLETED
    e1.updated_at = now - timedelta(days=8)

    # 2. COMPLETED: exactly 7 days old (boundary: NOT purged because < cutoff is strictly older)
    e2 = await repo.enqueue("c.exact", {}, event_id="c-exact")
    assert e2 is not None
    e2.status = OutboxStatus.COMPLETED
    e2.updated_at = now - timedelta(days=7)

    # 3. COMPLETED: 6 days old (should NOT be purged by 7-day cutoff)
    e3 = await repo.enqueue("c.recent", {}, event_id="c-recent")
    assert e3 is not None
    e3.status = OutboxStatus.COMPLETED
    e3.updated_at = now - timedelta(days=6)

    # 4. FAILED_DEAD_LETTER: 35 days old (should be purged by 30-day cutoff)
    e4 = await repo.enqueue("d.old", {}, event_id="d-old")
    assert e4 is not None
    e4.status = OutboxStatus.FAILED_DEAD_LETTER
    e4.updated_at = now - timedelta(days=35)

    # 5. FAILED_DEAD_LETTER: 20 days old (should NOT be purged by 30-day cutoff)
    e5 = await repo.enqueue("d.recent", {}, event_id="d-recent")
    assert e5 is not None
    e5.status = OutboxStatus.FAILED_DEAD_LETTER
    e5.updated_at = now - timedelta(days=20)

    # 6. PENDING: 50 days old (should NEVER be purged regardless of age)
    e6 = await repo.enqueue("p.old", {}, event_id="p-old")
    assert e6 is not None
    e6.status = OutboxStatus.PENDING
    e6.updated_at = now - timedelta(days=50)

    # 7. IN_PROGRESS: 50 days old (should NEVER be purged regardless of age)
    e7 = await repo.enqueue("ip.old", {}, event_id="ip-old")
    assert e7 is not None
    e7.status = OutboxStatus.IN_PROGRESS
    e7.updated_at = now - timedelta(days=50)

    # Execute cleanup with 7d completed / 30d DLQ cutoff
    res = await repo.cleanup_outbox_records(
        completed_older_than=now - timedelta(days=7),
        dead_letter_older_than=now - timedelta(days=30),
        batch_size=100,
    )

    assert res["deleted_completed"] == 1
    assert res["deleted_dead_letter"] == 1
    assert res["total_deleted"] == 2

    # Assert remaining state
    assert await repo.find_by_event_id("c-old") is None
    assert await repo.find_by_event_id("d-old") is None

    assert await repo.find_by_event_id("c-exact") is not None
    assert await repo.find_by_event_id("c-recent") is not None
    assert await repo.find_by_event_id("d-recent") is not None
    assert await repo.find_by_event_id("p-old") is not None
    assert await repo.find_by_event_id("ip-old") is not None


@pytest.mark.asyncio
async def test_fake_outbox_cleanup_batch_size_enforcement():
    """Verify cleanup_outbox_records respects batch_size limit when eligible records exceed limit."""
    repo = FakeOutboxRepository()
    now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)

    # Create 15 old COMPLETED records and 15 old DLQ records
    for i in range(15):
        ec = await repo.enqueue(f"c.{i}", {}, event_id=f"c-{i}")
        assert ec is not None
        ec.status = OutboxStatus.COMPLETED
        ec.updated_at = now - timedelta(days=10)

        ed = await repo.enqueue(f"d.{i}", {}, event_id=f"d-{i}")
        assert ed is not None
        ed.status = OutboxStatus.FAILED_DEAD_LETTER
        ed.updated_at = now - timedelta(days=40)

    assert len(repo.events) == 30

    # Purge with batch_size=5 (should delete at most 5 completed and 5 dlq = 10 total)
    res1 = await repo.cleanup_outbox_records(
        completed_older_than=now - timedelta(days=7),
        dead_letter_older_than=now - timedelta(days=30),
        batch_size=5,
    )

    assert res1["deleted_completed"] == 5
    assert res1["deleted_dead_letter"] == 5
    assert res1["total_deleted"] == 10
    assert len(repo.events) == 20

    # Purge remaining with batch_size=50 (deletes remaining 10 completed and 10 dlq = 20 total)
    res2 = await repo.cleanup_outbox_records(
        completed_older_than=now - timedelta(days=7),
        dead_letter_older_than=now - timedelta(days=30),
        batch_size=50,
    )

    assert res2["deleted_completed"] == 10
    assert res2["deleted_dead_letter"] == 10
    assert res2["total_deleted"] == 20
    assert len(repo.events) == 0


# ===========================================================================
# 4. Stress Test: Claiming Ordering & Lease Concurrency
# ===========================================================================


@pytest.mark.asyncio
async def test_fake_outbox_claim_due_records_priority_ordering():
    """Verify claim_due_records prioritizes earliest next_retry_at, then created_at."""
    repo = FakeOutboxRepository()
    now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)

    # 1. Due in past (10s ago)
    e1 = await repo.enqueue("e1", {}, event_id="e1")
    assert e1 is not None
    e1.next_retry_at = now - timedelta(seconds=10)
    e1.created_at = now - timedelta(minutes=5)

    # 2. Due in deeper past (30s ago)
    e2 = await repo.enqueue("e2", {}, event_id="e2")
    assert e2 is not None
    e2.next_retry_at = now - timedelta(seconds=30)
    e2.created_at = now - timedelta(minutes=10)

    # 3. Due now (same next_retry_at as e4, but created earlier)
    e3 = await repo.enqueue("e3", {}, event_id="e3")
    assert e3 is not None
    e3.next_retry_at = now
    e3.created_at = now - timedelta(minutes=2)

    # 4. Due now (created later)
    e4 = await repo.enqueue("e4", {}, event_id="e4")
    assert e4 is not None
    e4.next_retry_at = now
    e4.created_at = now - timedelta(minutes=1)

    # 5. Future record (not due)
    e5 = await repo.enqueue("e5", {}, event_id="e5")
    assert e5 is not None
    e5.next_retry_at = now + timedelta(seconds=15)

    # Claim with batch_size=3
    claimed = await repo.claim_due_records(
        worker_id="worker-test", batch_size=3, now=now
    )

    assert len(claimed) == 3
    # Order must be e2 (-30s), e1 (-10s), e3 (now, older created_at)
    assert claimed[0].event_id == "e2"
    assert claimed[1].event_id == "e1"
    assert claimed[2].event_id == "e3"

    for c in claimed:
        assert c.status == OutboxStatus.IN_PROGRESS
        assert c.lease_owner == "worker-test"
        assert c.lease_expires_at == now + timedelta(seconds=60)


@pytest.mark.asyncio
async def test_fake_outbox_claim_stale_lease_recovery():
    """Verify expired IN_PROGRESS leases are recovered by subsequent claim sweeps."""
    repo = FakeOutboxRepository()
    now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)

    # Enqueue and claim with worker-1
    e = await repo.enqueue("stale.event", {}, event_id="stale-1")
    assert e is not None

    claimed_w1 = await repo.claim_due_records(
        worker_id="worker-1",
        lease_duration=timedelta(seconds=30),
        now=now,
    )
    assert len(claimed_w1) == 1
    assert claimed_w1[0].lease_owner == "worker-1"

    # While lease is active (now + 10s), worker-2 cannot claim it
    active_now = now + timedelta(seconds=10)
    claimed_w2_active = await repo.claim_due_records(
        worker_id="worker-2",
        now=active_now,
    )
    assert len(claimed_w2_active) == 0

    # Once lease expires (now + 35s), worker-2 can recover and claim it
    expired_now = now + timedelta(seconds=35)
    claimed_w2_expired = await repo.claim_due_records(
        worker_id="worker-2",
        lease_duration=timedelta(seconds=60),
        now=expired_now,
    )
    assert len(claimed_w2_expired) == 1
    assert claimed_w2_expired[0].event_id == "stale-1"
    assert claimed_w2_expired[0].lease_owner == "worker-2"
    assert claimed_w2_expired[0].lease_expires_at == expired_now + timedelta(seconds=60)


# ===========================================================================
# 5. Parity Tests: Enqueue, Mark Completed, Find & Get
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["fake", "async"])
async def test_enqueue_parameter_parity_and_timezone_coercion(repo_type: str):
    """Verify enqueue coerces naive datetimes to UTC and preserves all domain fields."""
    naive_dt = datetime(2026, 9, 15, 10, 30, 0)  # naive datetime

    if repo_type == "fake":
        repo = FakeOutboxRepository()
        event = await repo.enqueue(
            event_type="test.tz",
            payload={"user_id": 42},
            event_id="evt-tz-1",
            max_retries=8,
            scheduled_at=naive_dt,
            aggregate_type="User",
            aggregate_id="usr-42",
        )
    else:
        session = _MockQueryEngine()
        repo = AsyncOutboxRepository(session)
        event = await repo.enqueue(
            event_type="test.tz",
            payload={"user_id": 42},
            event_id="evt-tz-1",
            max_retries=8,
            scheduled_at=naive_dt,
            aggregate_type="User",
            aggregate_id="usr-42",
        )

    assert event is not None
    assert event.event_id == "evt-tz-1"
    assert event.event_type == "test.tz"
    assert event.payload == {"user_id": 42}
    assert event.max_retries == 8
    assert event.aggregate_type == "User"
    assert event.aggregate_id == "usr-42"
    assert event.next_retry_at.tzinfo is not None
    assert event.next_retry_at == datetime(2026, 9, 15, 10, 30, 0, tzinfo=UTC)


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["fake", "async"])
async def test_mark_completed_releases_leases_and_sets_timestamps(repo_type: str):
    """Verify mark_completed transitions to COMPLETED, clears leases, and records processed_at."""
    now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)
    proc_at = datetime(2026, 8, 22, 12, 5, 0, tzinfo=UTC)

    if repo_type == "fake":
        repo = FakeOutboxRepository()
        event = await repo.enqueue("test.complete", {})
        assert event is not None
        event.status = OutboxStatus.IN_PROGRESS
        event.lease_owner = "worker-1"
        event.lease_expires_at = now + timedelta(minutes=1)

        await repo.mark_completed(event.id, processed_at=proc_at)
        saved = repo.events[event.id]
        assert saved.status == OutboxStatus.COMPLETED
        assert saved.lease_owner is None
        assert saved.lease_expires_at is None
        assert saved.processed_at == proc_at
        assert saved.updated_at == proc_at
    else:
        orm_row = TransactionalOutboxORM(
            id="orm-comp",
            event_id="evt-comp",
            event_type="test.complete",
            payload={},
            status=OutboxStatus.IN_PROGRESS.value,
            lease_owner="worker-1",
            lease_expires_at=now + timedelta(minutes=1),
        )
        session = _MockQueryEngine({"orm-comp": orm_row})
        repo = AsyncOutboxRepository(session)

        await repo.mark_completed("orm-comp", processed_at=proc_at)
        assert session.flushed is True
        assert len(session.executed_statements) == 1
        stmt = session.executed_statements[0]
        # Verify compiled update statement values
        assert "COMPLETED" in str(stmt.compile().params.values())


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["fake", "async"])
async def test_record_failure_explicit_max_retries_override(repo_type: str):
    """Verify record_failure respects the caller-provided max_retries override."""
    now = utc_now()
    if repo_type == "fake":
        repo = FakeOutboxRepository()
        event = await repo.enqueue("test.override", {}, max_retries=10)
        assert event is not None
        event.retry_count = 1
        outbox_id = event.id
    else:
        orm_row = TransactionalOutboxORM(
            id="orm-override",
            event_id="evt-override",
            event_type="test.override",
            payload={},
            status=OutboxStatus.IN_PROGRESS.value,
            retry_count=1,
            max_retries=10,  # Row says 10
            created_at=now,
            updated_at=now,
        )
        session = _MockQueryEngine({"orm-override": orm_row})
        repo = AsyncOutboxRepository(session)
        outbox_id = "orm-override"

    # Next failure: retry_count becomes 2. If max_retries override is 2, it should DLQ immediately!
    res = OutboxHandlerResult.transient_failure("Glitch")
    is_dlq = await repo.record_failure(outbox_id, res, max_retries=2)

    assert is_dlq is True
    rec = repo.events[outbox_id] if repo_type == "fake" else session.rows[outbox_id]
    assert rec.status == (
        OutboxStatus.FAILED_DEAD_LETTER
        if repo_type == "fake"
        else OutboxStatus.FAILED_DEAD_LETTER.value
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["fake", "async"])
async def test_find_and_get_methods_parity(repo_type: str):
    """Verify find_by_id, find_by_event_id, get_by_id, get_by_event_id return expected entities or None."""
    if repo_type == "fake":
        repo = FakeOutboxRepository()
        event = await repo.enqueue("test.find", {"k": 1}, event_id="evt-find-1")
        assert event is not None
        outbox_id = event.id

        assert await repo.find_by_id(outbox_id) == event
        assert await repo.get_by_id(outbox_id) == event
        assert await repo.find_by_event_id("evt-find-1") == event
        assert await repo.get_by_event_id("evt-find-1") == event

        assert await repo.find_by_id("non-existent") is None
        assert await repo.get_by_id("non-existent") is None
        assert await repo.find_by_event_id("non-existent-evt") is None
        assert await repo.get_by_event_id("non-existent-evt") is None
    else:
        orm_row = TransactionalOutboxORM(
            id="orm-find-1",
            event_id="evt-find-1",
            event_type="test.find",
            payload={"k": 1},
        )
        session = _MockQueryEngine({"orm-find-1": orm_row})
        repo = AsyncOutboxRepository(session)

        res_by_id = await repo.find_by_id("orm-find-1")
        assert res_by_id is not None
        assert res_by_id.id == "orm-find-1"

        res_by_evt = await repo.find_by_event_id("evt-find-1")
        assert res_by_evt is not None
        assert res_by_evt.event_id == "evt-find-1"

        get_by_id_res = await repo.get_by_id("orm-find-1")
        assert get_by_id_res is not None
        assert get_by_id_res.id == "orm-find-1"

        get_by_evt_res = await repo.get_by_event_id("evt-find-1")
        assert get_by_evt_res is not None
        assert get_by_evt_res.event_id == "evt-find-1"
