"""Adversarial empirical stress-tests for OutboxDispatchEngine and pluggable handlers.

Milestones M2, M3, M4 Empirical Verification Suite:
- Semaphore throttling under high concurrent loads
- Failure classification: Transient vs Permanent vs Unregistered
- Dead-letter transitions and retry budget boundary conditions
- Sentry alert capture and safe observability metric/log emissions
- Stale lease reclamation and retention cleanup invariants
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.domain.models.outbox_status import OutboxEvent, OutboxStatus
from src.domain.ports.outbox_handler_port import (
    OutboxEventContext,
    OutboxHandlerResult,
)
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.outbox_event import TransactionalOutboxORM
from src.infra.repositories.outbox_repository import AsyncOutboxRepository
from src.infra.services.handlers import (
    AffiliateWebhookHandler,
    PushNotificationHandler,
    TelemetryHandler,
    create_default_handler_registry,
)
from src.infra.services.outbox_dispatch_engine import (
    OutboxDispatchEngine,
    _ClaimedOutboxItem,
)
from src.infra.services.outbox_handler_registry import OutboxHandlerRegistry

# ---------------------------------------------------------------------------
# Test Helpers & Mock Fixtures
# ---------------------------------------------------------------------------


def _make_mock_session_factory():
    """Creates a mock async session factory simulating short transactions."""

    def _factory():
        session = MagicMock()
        begin_cm = AsyncMock()
        begin_cm.__aenter__.return_value = session
        begin_cm.__aexit__.return_value = False
        session.begin = MagicMock(return_value=begin_cm)

        cm = AsyncMock()
        cm.__aenter__.return_value = session
        cm.__aexit__.return_value = False
        return cm

    return _factory


# ---------------------------------------------------------------------------
# 1. Semaphore Throttling & High Concurrency Stress-Tests
# ---------------------------------------------------------------------------


class TestConcurrencyAndSemaphoreThrottling:
    @pytest.mark.asyncio
    async def test_semaphore_strictly_limits_concurrent_handler_executions(self):
        """Stress-test: 30 concurrent items dispatched with concurrency_limit=4.
        Verifies that active concurrent executions never exceed 4 at any moment.
        """
        concurrency_limit = 4
        total_items = 30

        active_concurrent = 0
        max_concurrent_seen = 0
        lock = asyncio.Lock()

        class SlowHandler:
            async def handle(
                self, payload: dict, context: OutboxEventContext
            ) -> OutboxHandlerResult:
                nonlocal active_concurrent, max_concurrent_seen
                async with lock:
                    active_concurrent += 1
                    if active_concurrent > max_concurrent_seen:
                        max_concurrent_seen = active_concurrent

                # Simulate async network I/O
                await asyncio.sleep(0.01)

                async with lock:
                    active_concurrent -= 1

                return OutboxHandlerResult.ok()

        registry = OutboxHandlerRegistry()
        registry.register("concurrent.test", SlowHandler())

        engine = OutboxDispatchEngine(
            registry=registry,
            concurrency_limit=concurrency_limit,
        )

        now = utc_now()
        items = [
            _ClaimedOutboxItem(
                id=f"out-{i}",
                event_id=f"evt-{i}",
                event_type="concurrent.test",
                payload={"index": i},
                retry_count=0,
                max_retries=5,
                created_at=now,
            )
            for i in range(total_items)
        ]

        results = await engine._phase2_dispatch_handlers(items)

        assert len(results) == total_items
        assert all(res.success is True for _, res in results)
        assert max_concurrent_seen <= concurrency_limit
        assert max_concurrent_seen >= 2  # Concurrency actually happened
        assert active_concurrent == 0

    @pytest.mark.asyncio
    async def test_single_concurrency_serializes_dispatching(self):
        """Stress-test: concurrency_limit=1 ensures strictly serial execution."""
        execution_order = []

        class OrderedHandler:
            async def handle(
                self, payload: dict, context: OutboxEventContext
            ) -> OutboxHandlerResult:
                execution_order.append(payload["idx"])
                await asyncio.sleep(0.005)
                return OutboxHandlerResult.ok()

        registry = OutboxHandlerRegistry()
        registry.register("serial.test", OrderedHandler())

        engine = OutboxDispatchEngine(
            registry=registry,
            concurrency_limit=1,
        )

        now = utc_now()
        items = [
            _ClaimedOutboxItem(
                id=f"out-{i}",
                event_id=f"evt-{i}",
                event_type="serial.test",
                payload={"idx": i},
                retry_count=0,
                max_retries=5,
                created_at=now,
            )
            for i in range(10)
        ]

        results = await engine._phase2_dispatch_handlers(items)
        assert len(results) == 10
        assert execution_order == list(range(10))


# ---------------------------------------------------------------------------
# 2. Handler Failure Classification: Transient vs Permanent
# ---------------------------------------------------------------------------


class TestHandlerFailureClassification:
    # --- AffiliateWebhookHandler ---

    @pytest.mark.asyncio
    async def test_affiliate_http_429_treated_as_transient(self):
        """HTTP 429 Rate Limit must be treated as transient so it can retry with backoff."""
        adapter = MagicMock()
        request = httpx.Request("POST", "http://affiliate")
        response = httpx.Response(429, request=request)
        adapter.send_event = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Rate limited", request=request, response=response
            )
        )
        handler = AffiliateWebhookHandler(adapter)

        context = OutboxEventContext(
            outbox_id="1",
            event_id="e1",
            event_type="affiliate_event",
            retry_count=0,
            created_at_iso="2026-08-22",
        )
        res = await handler.handle({"referral_code": "AFF"}, context)
        assert res.success is False
        assert res.is_transient is True
        assert res.status_code == 429
        assert res.error_type == "HTTPServerError"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
    async def test_affiliate_http_4xx_treated_as_permanent(self, status_code: int):
        adapter = MagicMock()
        request = httpx.Request("POST", "http://affiliate")
        response = httpx.Response(status_code, request=request)
        adapter.send_event = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Client error", request=request, response=response
            )
        )
        handler = AffiliateWebhookHandler(adapter)

        context = OutboxEventContext(
            outbox_id="1",
            event_id="e1",
            event_type="affiliate_event",
            retry_count=0,
            created_at_iso="2026-08-22",
        )
        res = await handler.handle({"referral_code": "AFF"}, context)
        assert res.success is False
        assert res.is_transient is False
        assert res.status_code == status_code
        assert res.error_type == "HTTPClientError"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [500, 502, 503, 504])
    async def test_affiliate_http_5xx_treated_as_transient(self, status_code: int):
        adapter = MagicMock()
        request = httpx.Request("POST", "http://affiliate")
        response = httpx.Response(status_code, request=request)
        adapter.send_event = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=request, response=response
            )
        )
        handler = AffiliateWebhookHandler(adapter)

        context = OutboxEventContext(
            outbox_id="1",
            event_id="e1",
            event_type="affiliate_event",
            retry_count=0,
            created_at_iso="2026-08-22",
        )
        res = await handler.handle({"referral_code": "AFF"}, context)
        assert res.success is False
        assert res.is_transient is True
        assert res.status_code == status_code
        assert res.error_type == "HTTPServerError"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_payload", ["string", [1, 2, 3], 12345, None])
    async def test_affiliate_invalid_payload_types_permanent_failure(
        self, invalid_payload
    ):
        handler = AffiliateWebhookHandler(MagicMock())
        context = OutboxEventContext(
            outbox_id="1",
            event_id="e1",
            event_type="affiliate_event",
            retry_count=0,
            created_at_iso="2026-08-22",
        )
        res = await handler.handle(invalid_payload, context)  # type: ignore[arg-type]
        assert res.success is False
        assert res.is_transient is False
        assert res.error_type == "InvalidPayload"

    # --- PushNotificationHandler ---

    @pytest.mark.asyncio
    async def test_push_empty_or_whitespace_topic_fails_permanently(self):
        handler = PushNotificationHandler(MagicMock())
        context = OutboxEventContext(
            outbox_id="1",
            event_id="e1",
            event_type="push",
            retry_count=0,
            created_at_iso="2026-08-22",
        )
        res = await handler.handle({"topic": "   ", "title": "T", "body": "B"}, context)
        assert res.success is False
        assert res.is_transient is False
        assert res.error_type == "ValidationError"

    @pytest.mark.asyncio
    async def test_push_firebase_not_initialized_is_transient(self):
        firebase = MagicMock()
        firebase.send_to_topic.return_value = {
            "success": False,
            "reason": "firebase_not_initialized",
        }
        handler = PushNotificationHandler(firebase)
        context = OutboxEventContext(
            outbox_id="1",
            event_id="e1",
            event_type="push",
            retry_count=0,
            created_at_iso="2026-08-22",
        )
        res = await handler.handle(
            {"topic": "news", "title": "T", "body": "B"}, context
        )
        assert res.success is False
        assert res.is_transient is True
        assert res.error_type == "FirebaseNotInitialized"

    @pytest.mark.asyncio
    async def test_push_no_tokens_for_user_is_permanent(self):
        firebase = MagicMock()
        firebase.send_notification.return_value = {
            "success": False,
            "reason": "no_tokens",
        }
        handler = PushNotificationHandler(firebase)
        context = OutboxEventContext(
            outbox_id="1",
            event_id="e1",
            event_type="push",
            retry_count=0,
            created_at_iso="2026-08-22",
        )
        res = await handler.handle(
            {"user_id": "usr-123", "title": "T", "body": "B"}, context
        )
        assert res.success is False
        assert res.is_transient is False
        assert res.error_type == "NoTokensForUser"

    # --- TelemetryHandler ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bad_payload",
        [
            {},
            {"distinct_id": ""},
            {"user_id": "   "},
            {"distinct_id": "u1", "properties": ["not", "dict"]},
            {"distinct_id": "u1", "properties": 123},
        ],
    )
    async def test_telemetry_malformed_payloads_fail_permanently(self, bad_payload):
        handler = TelemetryHandler(MagicMock())
        context = OutboxEventContext(
            outbox_id="1",
            event_id="e1",
            event_type="telemetry",
            retry_count=0,
            created_at_iso="2026-08-22",
        )
        res = await handler.handle(bad_payload, context)
        assert res.success is False
        assert res.is_transient is False
        assert res.error_type == "ValidationError"

    # --- Unregistered Event Routing ---

    @pytest.mark.asyncio
    async def test_unregistered_event_fails_permanently_to_dlq(self):
        registry = create_default_handler_registry()
        handler = registry.get_or_fallback("totally.unknown.event.type")

        context = OutboxEventContext(
            outbox_id="1",
            event_id="e1",
            event_type="totally.unknown.event.type",
            retry_count=0,
            created_at_iso="2026-08-22",
        )
        res = await handler.handle({"foo": "bar"}, context)
        assert res.success is False
        assert res.is_transient is False
        assert res.error_type == "UnregisteredEventType"


# ---------------------------------------------------------------------------
# 3. Dead-Letter Transitions & Retry Budget Boundary Conditions
# ---------------------------------------------------------------------------


class TestDeadLetterAndRetryBudget:
    @pytest.mark.asyncio
    async def test_retry_budget_exhaustion_moves_to_dlq_on_exact_boundary(self):
        """When retry_count reaches max_retries, it transitions to FAILED_DEAD_LETTER."""
        # Row with retry_count=2, max_retries=3. 1 more transient failure makes retry_count=3 == max_retries.
        row = TransactionalOutboxORM(
            id="out-dlq-1",
            event_id="evt-dlq-1",
            event_type="test.retry",
            payload={},
            status=OutboxStatus.IN_PROGRESS.value,
            retry_count=2,
            max_retries=3,
            lease_owner="worker-1",
            error_log=[],
        )

        session = MagicMock()
        scalars = MagicMock()
        scalars.first.return_value = row
        db_res = MagicMock()
        db_res.scalars.return_value = scalars
        session.execute = AsyncMock(return_value=db_res)
        session.flush = AsyncMock()

        repo = AsyncOutboxRepository(session)
        transient_error = OutboxHandlerResult.transient_failure(
            "Network timeout", error_type="Timeout"
        )

        is_dlq = await repo.record_failure("out-dlq-1", transient_error)

        assert is_dlq is True
        assert row.retry_count == 3
        assert row.status == OutboxStatus.FAILED_DEAD_LETTER.value
        assert row.lease_owner is None
        assert row.lease_expires_at is None
        assert len(row.error_log) == 1
        assert row.error_log[0]["attempt"] == 3
        assert row.error_log[0]["is_transient"] is True

    @pytest.mark.asyncio
    async def test_transient_failure_below_budget_reschedules_with_backoff(self):
        """When retry_count < max_retries, transient failure resets status to PENDING with next_retry_at."""
        now = utc_now()
        row = TransactionalOutboxORM(
            id="out-retry-1",
            event_id="evt-retry-1",
            event_type="test.retry",
            payload={},
            status=OutboxStatus.IN_PROGRESS.value,
            retry_count=0,
            max_retries=3,
            lease_owner="worker-1",
            error_log=[],
        )

        session = MagicMock()
        scalars = MagicMock()
        scalars.first.return_value = row
        db_res = MagicMock()
        db_res.scalars.return_value = scalars
        session.execute = AsyncMock(return_value=db_res)
        session.flush = AsyncMock()

        repo = AsyncOutboxRepository(session)
        transient_error = OutboxHandlerResult.transient_failure(
            "503 Unavailable", error_type="ServerError"
        )

        is_dlq = await repo.record_failure("out-retry-1", transient_error)

        assert is_dlq is False
        assert row.retry_count == 1
        assert row.status == OutboxStatus.PENDING.value
        assert row.lease_owner is None
        assert row.lease_expires_at is None
        assert row.next_retry_at > now
        assert len(row.error_log) == 1

    @pytest.mark.asyncio
    async def test_permanent_failure_immediately_moves_to_dlq_regardless_of_remaining_budget(
        self,
    ):
        """A permanent failure on retry 0 of 10 must immediately become FAILED_DEAD_LETTER."""
        row = TransactionalOutboxORM(
            id="out-perm-1",
            event_id="evt-perm-1",
            event_type="test.perm",
            payload={},
            status=OutboxStatus.IN_PROGRESS.value,
            retry_count=0,
            max_retries=10,
            lease_owner="worker-1",
            error_log=[],
        )

        session = MagicMock()
        scalars = MagicMock()
        scalars.first.return_value = row
        db_res = MagicMock()
        db_res.scalars.return_value = scalars
        session.execute = AsyncMock(return_value=db_res)
        session.flush = AsyncMock()

        repo = AsyncOutboxRepository(session)
        perm_error = OutboxHandlerResult.permanent_failure(
            "Invalid schema: missing field", error_type="SchemaError"
        )

        is_dlq = await repo.record_failure("out-perm-1", perm_error)

        assert is_dlq is True
        assert row.retry_count == 1
        assert row.status == OutboxStatus.FAILED_DEAD_LETTER.value


# ---------------------------------------------------------------------------
# 4. Sentry Alert Capture & Observability Invariants
# ---------------------------------------------------------------------------


class TestObservabilityAndSentryAlerts:
    @pytest.mark.asyncio
    async def test_sentry_alert_and_dead_letter_metric_emitted_on_dlq(self):
        mock_factory = _make_mock_session_factory()
        registry = OutboxHandlerRegistry()
        handler = MagicMock()
        handler.handle = AsyncMock(
            return_value=OutboxHandlerResult.permanent_failure(
                "Invalid payload format", error_type="InvalidPayload"
            )
        )
        registry.register("failing.event", handler)

        engine = OutboxDispatchEngine(
            registry=registry,
            session_factory=mock_factory,
        )

        now = utc_now()
        claimed = OutboxEvent(
            id="row-99",
            event_id="evt-99",
            event_type="failing.event",
            payload={},
            status=OutboxStatus.IN_PROGRESS,
            retry_count=0,
            max_retries=5,
            next_retry_at=now,
            created_at=now,
            updated_at=now,
        )

        with (
            patch(
                "src.infra.services.outbox_dispatch_engine.AsyncOutboxRepository.claim_due_records",
                new_callable=AsyncMock,
                return_value=[claimed],
            ),
            patch(
                "src.infra.services.outbox_dispatch_engine.AsyncOutboxRepository.record_failure",
                new_callable=AsyncMock,
                return_value=True,  # DLQ
            ),
            patch(
                "src.infra.services.outbox_dispatch_engine.capture_message"
            ) as mock_sentry,
            patch(
                "src.infra.services.outbox_dispatch_engine.increment_metric"
            ) as mock_metric,
            patch("src.infra.services.outbox_dispatch_engine.log_event") as mock_log,
        ):
            stats = await engine.run_once()

        assert stats["dead_letter"] == 1

        # Sentry alert verification
        mock_sentry.assert_called_once()
        sentry_msg = mock_sentry.call_args[0][0]
        assert "evt-99" in sentry_msg
        assert "failing.event" in sentry_msg
        assert mock_sentry.call_args[1]["level"] == "error"
        sentry_ctx = mock_sentry.call_args[1]["context"]
        assert sentry_ctx["component"] == "outbox_dispatcher"
        assert sentry_ctx["operation"] == "dead_letter"
        assert sentry_ctx["row_id"] == "row-99"
        assert sentry_ctx["event_id"] == "evt-99"
        assert sentry_ctx["event_type"] == "failing.event"
        assert sentry_ctx["error_type"] == "InvalidPayload"

        # Metric verification
        mock_metric.assert_called_with(
            "outbox.dead_letter",
            attributes={
                "component": "outbox_dispatcher",
                "event_type": "failing.event",
                "status": "failed_dead_letter",
            },
        )

        # Log verification
        mock_log.assert_called_once()
        assert mock_log.call_args[0][0] == "error"
        assert mock_log.call_args[1]["attributes"]["status"] == "failed_dead_letter"

    @pytest.mark.asyncio
    async def test_sentry_not_emitted_on_normal_retry(self):
        mock_factory = _make_mock_session_factory()
        registry = OutboxHandlerRegistry()
        handler = MagicMock()
        handler.handle = AsyncMock(
            return_value=OutboxHandlerResult.transient_failure(
                "Temporary connection reset", error_type="ConnectionReset"
            )
        )
        registry.register("retry.event", handler)

        engine = OutboxDispatchEngine(
            registry=registry,
            session_factory=mock_factory,
        )

        now = utc_now()
        claimed = OutboxEvent(
            id="row-100",
            event_id="evt-100",
            event_type="retry.event",
            payload={},
            status=OutboxStatus.IN_PROGRESS,
            retry_count=0,
            max_retries=5,
            next_retry_at=now,
            created_at=now,
            updated_at=now,
        )

        with (
            patch(
                "src.infra.services.outbox_dispatch_engine.AsyncOutboxRepository.claim_due_records",
                new_callable=AsyncMock,
                return_value=[claimed],
            ),
            patch(
                "src.infra.services.outbox_dispatch_engine.AsyncOutboxRepository.record_failure",
                new_callable=AsyncMock,
                return_value=False,  # Not DLQ (rescheduled)
            ),
            patch(
                "src.infra.services.outbox_dispatch_engine.capture_message"
            ) as mock_sentry,
            patch(
                "src.infra.services.outbox_dispatch_engine.increment_metric"
            ) as mock_metric,
        ):
            stats = await engine.run_once()

        assert stats["retried"] == 1
        assert stats["dead_letter"] == 0
        mock_sentry.assert_not_called()
        mock_metric.assert_called_with(
            "outbox.retried",
            attributes={
                "component": "outbox_dispatcher",
                "event_type": "retry.event",
                "status": "pending",
            },
        )


# ---------------------------------------------------------------------------
# 5. Worker Draining, Retention Invariants & Edge Cases
# ---------------------------------------------------------------------------


class TestWorkerDrainingAndEdgeCases:
    @pytest.mark.asyncio
    async def test_phase2_catches_unhandled_handler_crash(self):
        """If a pluggable handler raises an unexpected exception (e.g. ZeroDivisionError),
        it is caught, logged, and converted into a transient failure instead of crashing the batch.
        """
        registry = OutboxHandlerRegistry()
        crash_handler = MagicMock()
        crash_handler.handle = AsyncMock(
            side_effect=ZeroDivisionError("division by zero")
        )
        registry.register("crash.type", crash_handler)

        engine = OutboxDispatchEngine(
            registry=registry,
            session_factory=_make_mock_session_factory(),
        )

        now = utc_now()
        item = _ClaimedOutboxItem(
            id="out-crash",
            event_id="evt-crash",
            event_type="crash.type",
            payload={},
            retry_count=0,
            max_retries=3,
            created_at=now,
        )

        results = await engine._phase2_dispatch_handlers([item])
        assert len(results) == 1
        claimed_item, res = results[0]
        assert claimed_item.id == "out-crash"
        assert res.success is False
        assert res.is_transient is True
        assert res.error_type == "ZeroDivisionError"
        assert "division by zero" in (res.error_message or "")

    @pytest.mark.asyncio
    async def test_mixed_batch_dispatch_accurately_aggregates_stats(self):
        """A batch containing 1 success, 1 transient failure, 1 DLQ, and 1 unregistered event."""
        registry = OutboxHandlerRegistry()

        success_handler = MagicMock(
            handle=AsyncMock(return_value=OutboxHandlerResult.ok())
        )
        retry_handler = MagicMock(
            handle=AsyncMock(
                return_value=OutboxHandlerResult.transient_failure(
                    "503", error_type="503"
                )
            )
        )
        dlq_handler = MagicMock(
            handle=AsyncMock(
                return_value=OutboxHandlerResult.permanent_failure(
                    "400", error_type="400"
                )
            )
        )

        registry.register("event.success", success_handler)
        registry.register("event.retry", retry_handler)
        registry.register("event.dlq", dlq_handler)

        now = utc_now()
        items = [
            _ClaimedOutboxItem("1", "e1", "event.success", {}, 0, 5, now),
            _ClaimedOutboxItem("2", "e2", "event.retry", {}, 0, 5, now),
            _ClaimedOutboxItem("3", "e3", "event.dlq", {}, 0, 5, now),
            _ClaimedOutboxItem("4", "e4", "unregistered.event", {}, 0, 5, now),
        ]

        engine = OutboxDispatchEngine(
            registry=registry,
            session_factory=_make_mock_session_factory(),
        )

        async def _mock_record_failure(outbox_id, result, max_retries=5):
            # item 2 is transient, items 3 and 4 are permanent (DLQ)
            return not result.is_transient

        with (
            patch(
                "src.infra.services.outbox_dispatch_engine.AsyncOutboxRepository.claim_due_records",
                new_callable=AsyncMock,
                return_value=[
                    OutboxEvent(
                        id=it.id, event_id=it.event_id, event_type=it.event_type
                    )
                    for it in items
                ],
            ),
            patch(
                "src.infra.services.outbox_dispatch_engine.AsyncOutboxRepository.mark_completed",
                new_callable=AsyncMock,
            ) as mock_complete,
            patch(
                "src.infra.services.outbox_dispatch_engine.AsyncOutboxRepository.record_failure",
                side_effect=_mock_record_failure,
            ) as mock_fail,
            patch("src.infra.services.outbox_dispatch_engine.capture_message"),
            patch("src.infra.services.outbox_dispatch_engine.increment_metric"),
            patch("src.infra.services.outbox_dispatch_engine.log_event"),
        ):
            stats = await engine.run_once()

        assert stats["claimed"] == 4
        assert stats["completed"] == 1
        assert stats["retried"] == 1
        assert stats["dead_letter"] == 2
        mock_complete.assert_awaited_once_with("1")
        assert mock_fail.await_count == 3
