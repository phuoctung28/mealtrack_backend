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

import sentry_sdk
from sqlalchemy import text

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.config import engine
from src.infra.database.uow import UnitOfWork
from src.infra.monitoring.sentry import initialize_sentry
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
    initialize_sentry()

    # DB warm-up — triggers Neon compute wakeup; abort if unreachable
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("DB warm-up failed (Neon cold start?): %s", exc)
        sentry_sdk.flush(timeout=5)
        return

    firebase = FirebaseService()  # initialises firebase_admin internally
    now = utc_now()

    # Phase 1 — precompute notification rows for each timezone today
    # DailyContextPrecomputeService.precompute_for_timezone() is idempotent:
    # it checks an in-memory sentinel (fast) then a DB fallback, so re-running is free.
    try:
        with UnitOfWork() as uow:
            tz_rows = uow.session.execute(
                text("SELECT DISTINCT timezone FROM users WHERE timezone IS NOT NULL")
            ).fetchall()
        timezones = [r.timezone for r in tz_rows]
        precompute = DailyContextPrecomputeService()
        for tz_name in timezones:
            local_today = now.astimezone(ZoneInfo(tz_name)).date()
            await precompute.precompute_for_timezone(tz_name, local_today)
    except Exception:
        logger.exception("Phase 1 (precompute) failed")

    # Phase 2 — create trial-expiry push rows (T-2d / T-1d)
    # UNIQUE CONSTRAINT on (user_id, notification_type, scheduled_date)
    # prevents duplicates.
    try:
        trial_push = CronTrialPushService()
        await asyncio.to_thread(trial_push.check_and_schedule_pushes, now)
    except Exception:
        logger.exception("Phase 2 (trial push scheduling) failed")

    dispatch = CronNotificationDispatchService(firebase)

    # Phase 3 — claim due rows, render messages, batch FCM send, mark sent
    # status='processing' claim prevents double-sends on concurrent runs.
    try:
        await dispatch._send_due_notifications(now)
    except Exception:
        logger.exception("Phase 3 (FCM dispatch) failed")

    # Phase 4 — delete expired rows that are no longer eligible for dispatch
    try:
        await asyncio.to_thread(dispatch.cleanup_expired_notifications)
    except Exception:
        logger.exception("Phase 4 (notification cleanup) failed")

    engine.dispose()
    sentry_sdk.flush(timeout=5)


if __name__ == "__main__":
    asyncio.run(run())
