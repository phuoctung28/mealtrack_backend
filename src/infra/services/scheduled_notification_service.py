"""
Scheduled notification service — batch pre-compute + batch send.

Architecture:
  Phase 1 (every tick): detect which timezones just hit local midnight →
          trigger DailyContextPrecomputeService for that group.
  Phase 2 (every tick): fetch due notifications from PostgreSQL →
          read calories_consumed from Redis → render messages →
          batch FCM send → mark sent.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import bindparam, text

from src.domain.model.notification import NotificationType
from src.domain.services.notification_messages import get_messages
from src.domain.services.notification_service import DEACTIVATABLE_FCM_ERRORS
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.redis_client import RedisClient
from src.infra.database.uow import UnitOfWork
from src.infra.repositories.notification.reminder_query_builder import (
    ReminderQueryBuilder,
)
from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)
from src.infra.services.firebase_service import FirebaseService
from src.infra.services.scheduler_leader_lock import SchedulerLeaderLock

logger = logging.getLogger(__name__)

_CLEANUP_TICKS = 60  # clean expired notifications every ~60 min


def _timezones_at_midnight(tz_names: list[str], now_utc: datetime) -> list[str]:
    """Return timezone names where local time is currently HH:MM == 00:00."""
    result = []
    for tz_name in tz_names:
        try:
            local = now_utc.astimezone(ZoneInfo(tz_name))
            if local.hour == 0 and local.minute == 0:
                result.append(tz_name)
        except Exception:
            pass
    return result


class ScheduledNotificationService:
    """Batch-sends scheduled notifications. One leader per host via flock."""

    LOOP_INTERVAL_SECONDS = 60
    LOOP_ERROR_RETRY_SECONDS = 30

    def __init__(self, firebase_service: FirebaseService, redis_client: RedisClient):
        self._firebase = firebase_service
        self._redis = redis_client
        self._precompute = DailyContextPrecomputeService(redis_client)
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._leader_lock = SchedulerLeaderLock()
        self._leader_acquired = False
        self._cleanup_counter = 0
        self._distinct_timezones: list[str] = []

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            logger.warning("Scheduler already running")
            return
        if not self._leader_lock.try_acquire():
            logger.info("Scheduler skipped: another worker holds the lock")
            return
        self._leader_acquired = True
        self._running = True
        self._distinct_timezones = await asyncio.to_thread(
            self._fetch_distinct_timezones
        )
        self._tasks.append(asyncio.create_task(self._scheduling_loop()))
        self._tasks.append(asyncio.create_task(self._startup_catchup()))
        logger.info("Scheduled notification service started (leader)")

    async def stop(self) -> None:
        if not self._leader_acquired:
            return
        self._running = False
        for t in self._tasks:
            if not t.done():
                t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._leader_lock.release()
        self._leader_acquired = False
        logger.info("Scheduled notification service stopped")

    def is_running(self) -> bool:
        return self._running

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _scheduling_loop(self) -> None:
        while self._running:
            try:
                now = utc_now()
                await self._check_midnight_precompute(now)
                await self._send_due_notifications(now)
                self._cleanup_counter += 1
                if self._cleanup_counter >= _CLEANUP_TICKS:
                    self._cleanup_counter = 0
                    await asyncio.to_thread(self._cleanup_expired_notifications)
                await asyncio.sleep(self.LOOP_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Scheduler loop error: %s", exc)
                await asyncio.sleep(self.LOOP_ERROR_RETRY_SECONDS)

    # ── Startup catch-up ──────────────────────────────────────────────────────

    async def _startup_catchup(self) -> None:
        """Pre-compute context for all timezones that missed today's midnight run."""
        now = utc_now()
        for tz_name in self._distinct_timezones:
            try:
                today = now.astimezone(ZoneInfo(tz_name)).date()
                await self._precompute.precompute_for_timezone(tz_name, today)
            except Exception as exc:
                logger.error("Startup catch-up failed for %s: %s", tz_name, exc)
        logger.info(
            "Startup catch-up complete for %d timezones", len(self._distinct_timezones)
        )

    # ── Phase 1: Midnight pre-compute ─────────────────────────────────────────

    async def _check_midnight_precompute(self, now: datetime) -> None:
        """For each timezone currently at local midnight, trigger pre-compute."""
        at_midnight = _timezones_at_midnight(self._distinct_timezones, now)
        for tz_name in at_midnight:
            try:
                # Use the local date for this timezone, not the UTC date
                today = now.astimezone(ZoneInfo(tz_name)).date()
                await self._precompute.precompute_for_timezone(tz_name, today)
            except Exception as exc:
                logger.error("Pre-compute failed for %s: %s", tz_name, exc)

    # ── Phase 2: Send due notifications ───────────────────────────────────────

    async def _send_due_notifications(self, now: datetime) -> None:
        """Fetch due rows, pull consumed from Redis, render, batch FCM, mark sent."""

        def _fetch_due():
            with UnitOfWork() as uow:
                return ReminderQueryBuilder.find_due_notifications(uow.session, now)

        due = await asyncio.to_thread(_fetch_due)
        if not due:
            return

        logger.info("Sending %d due notifications", len(due))

        # Batch-fetch calories_consumed from Redis
        context_keys = [f"user_daily_context:{n.user_id}" for n in due]
        redis_contexts = await self._redis.hgetall_batch(context_keys)

        # Render messages per notification and group by (type, title, body)
        groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        sent_ids = []
        failed_ids = []

        for notif, redis_ctx in zip(due, redis_contexts):
            ctx = notif.context  # JSONB dict from PostgreSQL
            tokens = ctx.get("fcm_tokens", [])
            if not tokens:
                failed_ids.append(notif.id)
                continue

            calorie_goal = int(ctx.get("calorie_goal", 2000))
            gender = ctx.get("gender", "male")
            lang = ctx.get("language_code", "en")

            if notif.notification_type == "daily_summary":
                # Use JSONB snapshot from midnight pre-compute (stable for full-day summary)
                calories_consumed = int(ctx.get("calories_consumed", 0))
            else:
                # Use Redis for meal reminders (fresher, ~30 min stale)
                if not redis_ctx:
                    logger.warning(
                        "Redis cache miss for user %s — using calorie_goal only",
                        notif.user_id,
                    )
                    calories_consumed = 0
                else:
                    calories_consumed = int(redis_ctx.get("calories_consumed", 0))

            remaining = max(0, calorie_goal - calories_consumed)
            title, body = _render_message(
                notif.notification_type,
                remaining,
                gender,
                lang,
                calories_consumed=calories_consumed,
                calorie_goal=calorie_goal,
            )
            for tok in tokens:
                groups[(notif.notification_type, title, body)].append(tok)
            sent_ids.append(notif.id)

        # Batch FCM — 500 tokens per call
        for (notif_type, title, body), tokens in groups.items():
            for chunk in _chunked(tokens, 500):
                result = self._firebase.send_multicast(
                    tokens=chunk, title=title, body=body, notification_type=notif_type
                )
                if result.get("failed_tokens"):
                    await self._handle_failed_tokens(result["failed_tokens"])

        # Mark sent/failed
        if sent_ids or failed_ids:
            await asyncio.to_thread(self._mark_notifications, sent_ids, failed_ids)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _fetch_distinct_timezones(self) -> list[str]:
        with UnitOfWork() as uow:
            rows = uow.session.execute(
                text("SELECT DISTINCT timezone FROM users WHERE timezone IS NOT NULL")
            ).fetchall()
            return [r.timezone for r in rows]

    def _mark_notifications(self, sent_ids: list[str], failed_ids: list[str]) -> None:
        with UnitOfWork() as uow:
            if sent_ids:
                uow.session.execute(
                    text(
                        "UPDATE notifications SET status = 'sent' WHERE id IN :ids"
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": sent_ids},
                )
            if failed_ids:
                uow.session.execute(
                    text(
                        "UPDATE notifications SET status = 'failed' WHERE id IN :ids"
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": failed_ids},
                )

    def _cleanup_expired_notifications(self) -> None:
        with UnitOfWork() as uow:
            result = uow.session.execute(
                text("DELETE FROM notifications WHERE expires_at < NOW()")
            )
            logger.info("Cleaned up %d expired notification rows", result.rowcount)

    async def _handle_failed_tokens(self, failed_tokens: list[dict]) -> None:
        to_deactivate = [
            ft["token"]
            for ft in failed_tokens
            if any(
                code in str(ft.get("error", "")).upper()
                for code in DEACTIVATABLE_FCM_ERRORS
            )
        ]
        if to_deactivate:
            await asyncio.to_thread(self._deactivate_tokens, to_deactivate)

    def _deactivate_tokens(self, tokens: list[str]) -> None:
        with UnitOfWork() as uow:
            uow.session.execute(
                text(
                    "UPDATE user_fcm_tokens SET is_active = false WHERE fcm_token IN :tokens"
                ).bindparams(bindparam("tokens", expanding=True)),
                {"tokens": tokens},
            )

    async def send_test_notification(self, user_id: str) -> Dict:
        """Send a test notification to a user (on-demand, no pre-compute)."""
        tokens = await asyncio.to_thread(self._get_tokens_for_user, user_id)
        if not tokens:
            return {"success": False, "reason": "no_tokens"}
        return await asyncio.to_thread(
            self._firebase.send_multicast,
            tokens,
            "Test Notification",
            "This is a test notification from the backend",
            str(NotificationType.DAILY_SUMMARY),
        )

    def _get_tokens_for_user(self, user_id: str) -> list[str]:
        with UnitOfWork() as uow:
            rows = uow.session.execute(
                text(
                    "SELECT fcm_token FROM user_fcm_tokens WHERE user_id = :uid AND is_active = true"
                ),
                {"uid": user_id},
            ).fetchall()
            return [r.fcm_token for r in rows]


# ── Module-level helpers ───────────────────────────────────────────────────────


def _render_message(
    notification_type: str,
    remaining: int,
    gender: str,
    lang: str,
    calories_consumed: int = 0,
    calorie_goal: int = 2000,
) -> tuple[str, str]:
    """Render title + body for a notification type."""
    messages = get_messages(lang, gender)
    if notification_type == "meal_reminder_breakfast":
        cfg = messages["meal_reminder"]["breakfast"]
        return cfg["title"], cfg.get("body", "")
    elif notification_type == "meal_reminder_lunch":
        cfg = messages["meal_reminder"]["lunch"]
        return cfg["title"], cfg["body_template"].format(remaining=remaining)
    elif notification_type == "meal_reminder_dinner":
        cfg = messages["meal_reminder"]["dinner"]
        return cfg["title"], cfg["body_template"].format(remaining=remaining)
    elif notification_type == "daily_summary":
        summary = messages["daily_summary"]
        if calories_consumed == 0:
            cfg = summary["zero_logs"]
            return cfg["title"], cfg["body"]
        pct = (calories_consumed / calorie_goal * 100) if calorie_goal > 0 else 0
        if 95 <= pct <= 105:
            cfg = summary["on_target"]
            return cfg["title"], cfg["body_template"].format(percentage=int(pct))
        elif pct < 95:
            cfg = summary["under_goal"]
            return cfg["title"], cfg["body_template"].format(
                deficit=int(calorie_goal - calories_consumed)
            )
        elif pct <= 120:
            cfg = summary["slightly_over"]
            return cfg["title"], cfg["body_template"].format(
                excess=int(calories_consumed - calorie_goal)
            )
        else:
            cfg = summary["way_over"]
            return cfg["title"], cfg["body_template"].format(
                excess=int(calories_consumed - calorie_goal)
            )
    return "Notification", ""


def _chunked(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]
