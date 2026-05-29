"""
Push notification cron entry point.

Run manually:  python -m src.cron.push
Render cron schedule:  */2 * * * *

Phases (all idempotent — safe to run concurrently):
  1. Precompute — insert NotificationORM rows for every user/timezone today
  2. Trial push — insert T-2d / T-1d trial-expiry rows
  3. Dispatch   — claim pending rows, send via FCM, mark sent
"""
import asyncio
import logging

import sentry_sdk
from sqlalchemy import text
from zoneinfo import ZoneInfo

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.config import engine
from src.infra.database.uow import UnitOfWork
from src.infra.monitoring.sentry import initialize_sentry
from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService
from src.infra.services.firebase_service import FirebaseService
from src.infra.services.scheduled_notification_service import ScheduledNotificationService
from src.infra.services.scheduled_subscription_push_service import ScheduledSubscriptionPushService

logger = logging.getLogger(__name__)


async def run() -> None:
    """Execute all three notification phases then exit."""
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
    # UNIQUE CONSTRAINT on (user_id, notification_type, scheduled_date) prevents duplicates.
    try:
        trial_push = ScheduledSubscriptionPushService()
        await asyncio.to_thread(trial_push.check_and_schedule_pushes, now)
    except Exception:
        logger.exception("Phase 2 (trial push scheduling) failed")

    # Phase 3 — claim due rows, render messages, batch FCM send, mark sent
    # status='processing' claim prevents double-sends on concurrent runs.
    try:
        svc = ScheduledNotificationService(firebase, trial_push_service=None)
        await svc._send_due_notifications(now)
    except Exception:
        logger.exception("Phase 3 (FCM dispatch) failed")

    engine.dispose()
    sentry_sdk.flush(timeout=5)


if __name__ == "__main__":
    asyncio.run(run())
