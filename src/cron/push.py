"""
Push notification cron entry point.

Run manually:  python -m src.cron.push
Render cron schedule:  */2 * * * *

Phases (all idempotent — safe to run concurrently):
  1. Precompute — insert NotificationORM rows for every user/timezone today
  2. Trial push — insert T-2d / T-1d trial-expiry rows
  3. Dispatch   — claim pending rows, send via FCM, mark sent
  4. Cleanup    — remove expired notification rows
"""

import asyncio
import logging
from zoneinfo import ZoneInfo

from sqlalchemy import text

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.config_async import async_engine
from src.infra.monitoring import (
    capture_exception,
    flush_observability,
    initialize_observability,
    start_span,
)
from src.infra.services.cron_notification_dispatch_service import (
    CronNotificationDispatchService,
)
from src.infra.services.cron_trial_push_service import (
    CronTrialPushService,
)
from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)
from src.infra.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)


async def run() -> None:
    """Execute all notification cron phases then exit."""
    logging.basicConfig(level=logging.INFO)
    initialize_observability()

    # DB warm-up — triggers Neon compute wakeup; abort if unreachable
    try:
        with start_span(operation="cron.db_warmup", description="push cron DB warm-up"):
            if async_engine is None:
                raise RuntimeError("Async database engine is not initialized")
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("DB warm-up failed (Neon cold start?): %s", exc)
        capture_exception(
            exc,
            context={"component": "cron.push", "operation": "db_warmup"},
        )
        flush_observability(timeout=5)
        return

    firebase = FirebaseService()  # initialises firebase_admin internally
    now = utc_now()

    # Phase 1 — precompute notification rows for each timezone today
    # DailyContextPrecomputeService.precompute_for_timezone() is idempotent:
    # it checks an in-memory sentinel (fast) then a DB fallback, so re-running is free.
    try:
        with start_span(
            operation="cron.push.precompute", description="daily context precompute"
        ):
            async with async_engine.connect() as conn:
                tz_result = await conn.execute(
                    text(
                        "SELECT DISTINCT timezone FROM users WHERE timezone IS NOT NULL"
                    )
                )
                tz_rows = tz_result.fetchall()
            timezones = [r.timezone for r in tz_rows]
            precompute = DailyContextPrecomputeService()
            for tz_name in timezones:
                local_today = now.astimezone(ZoneInfo(tz_name)).date()
                await precompute.precompute_for_timezone(tz_name, local_today)
    except Exception as exc:
        logger.exception("Phase 1 (precompute) failed")
        capture_exception(
            exc,
            context={"component": "cron.push", "operation": "precompute"},
        )

    # Phase 2 — create trial-expiry push rows (T-2d / T-1d)
    # UNIQUE CONSTRAINT on (user_id, notification_type, scheduled_date)
    # prevents duplicates.
    try:
        with start_span(
            operation="cron.push.trial", description="trial push scheduling"
        ):
            trial_push = CronTrialPushService()
            await trial_push.check_and_schedule_pushes(now)
    except Exception as exc:
        logger.exception("Phase 2 (trial push scheduling) failed")
        capture_exception(
            exc,
            context={"component": "cron.push", "operation": "trial_push"},
        )

    dispatch = CronNotificationDispatchService(firebase)

    # Phase 3 — claim due rows, render messages, batch FCM send, mark sent
    # status='processing' claim prevents double-sends on concurrent runs.
    try:
        with start_span(operation="cron.push.dispatch", description="FCM dispatch"):
            await dispatch._send_due_notifications(now)
    except Exception as exc:
        logger.exception("Phase 3 (FCM dispatch) failed")
        capture_exception(
            exc,
            context={"component": "cron.push", "operation": "fcm_dispatch"},
        )

    # Phase 4 — delete expired rows that are no longer eligible for dispatch
    try:
        with start_span(
            operation="cron.push.cleanup", description="notification cleanup"
        ):
            await dispatch.cleanup_expired_notifications()
    except Exception as exc:
        logger.exception("Phase 4 (notification cleanup) failed")
        capture_exception(
            exc,
            context={"component": "cron.push", "operation": "cleanup"},
        )

    if async_engine is not None:
        await async_engine.dispose()
    flush_observability(timeout=5)


if __name__ == "__main__":
    asyncio.run(run())
