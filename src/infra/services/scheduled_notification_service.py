"""
Scheduled notification service — batch pre-compute + batch send.

Architecture:
  Phase 1 (every tick): detect which timezones just hit local midnight →
          trigger DailyContextPrecomputeService for that group.
  Phase 2 (every tick): fetch due notifications from PostgreSQL →
          fetch calories_consumed from DB → render messages →
          batch FCM send → mark sent.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import bindparam, text

from src.domain.model.notification import NotificationType
from src.domain.services.notification_messages import get_messages
from src.domain.services.notification_service import DEACTIVATABLE_FCM_ERRORS
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.uow import UnitOfWork
from src.infra.repositories.notification.reminder_query_builder import (
    ReminderQueryBuilder,
)
from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)
from src.infra.services.firebase_service import FirebaseService
from src.infra.services.scheduled_subscription_push_service import (
    ScheduledSubscriptionPushService,
)
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

    def __init__(
        self,
        firebase_service: FirebaseService,
        trial_push_service: "ScheduledSubscriptionPushService | None" = None,
    ):
        self._firebase = firebase_service
        self._precompute = DailyContextPrecomputeService()
        self._trial_push = trial_push_service
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._leader_lock = SchedulerLeaderLock()
        self._leader_acquired = False
        self._cleanup_counter = 0
        self._distinct_timezones: list[str] = []

        if self._trial_push is None:
            logger.warning(
                "ScheduledNotificationService constructed without "
                "trial_push_service — trial reminders disabled"
            )
        else:
            logger.info("ScheduledNotificationService: trial_push scheduler active")

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
                await asyncio.sleep(_seconds_until_next_minute(now))
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

        if self._trial_push is not None:
            try:
                await asyncio.to_thread(self._trial_push.check_and_schedule_pushes, now)
            except Exception:
                logger.exception("Startup trial-push catchup failed")

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

            if self._trial_push is not None:
                try:
                    await asyncio.to_thread(
                        self._trial_push.check_and_schedule_pushes, now
                    )
                except Exception:
                    logger.exception("Trial-push scheduling failed for tz=%s", tz_name)

    # ── Phase 2: Send due notifications ───────────────────────────────────────

    async def _send_due_notifications(self, now: datetime) -> None:
        """Fetch due rows, fetch calories_consumed from DB, render, batch FCM, mark sent."""

        def _claim_due():
            with UnitOfWork() as uow:
                due_rows = ReminderQueryBuilder.find_due_notifications(
                    uow.session, now, lock_rows=True
                )
                for row in due_rows:
                    row.status = "processing"
                return due_rows

        due = await asyncio.to_thread(_claim_due)
        if not due:
            return

        logger.info("Sending %d claimed due notifications", len(due))

        # Batch-fetch real-time calories_consumed from DB for meal reminders.
        # daily_summary uses the JSONB snapshot; trial_expiry ignores calories.
        meal_reminder_ids = [
            n.user_id for n in due
            if n.notification_type.startswith("meal_reminder")
        ]
        consumed_map: dict[str, int] = {}
        if meal_reminder_ids:
            consumed_map = await asyncio.to_thread(
                _fetch_calories_consumed_batch, meal_reminder_ids, now
            )

        hydration_user_ids = [
            n.user_id for n in due
            if n.notification_type.startswith("hydration_reminder")
        ]
        hydration_map: dict[str, tuple[int, int]] = {}
        if hydration_user_ids:
            try:
                hydration_map = await asyncio.to_thread(
                    _fetch_hydration_data_batch, hydration_user_ids, now
                )
            except Exception as exc:
                logger.warning("Failed to fetch hydration data batch: %s", exc)

        # Render messages per notification and group by (type, title, body)
        groups: dict[tuple[str, str, str], dict[str, list[str]]] = defaultdict(
            lambda: {"tokens": [], "ids": []}
        )
        sent_ids = []
        failed_ids = []

        for notif in due:
            ctx = notif.context  # JSONB dict from PostgreSQL
            tokens = ctx.get("fcm_tokens", [])
            if not tokens:
                failed_ids.append(notif.id)
                continue

            calorie_goal = int(ctx.get("calorie_goal", 2000))
            gender = ctx.get("gender", "male")
            lang = ctx.get("language_code", "en")

            if notif.notification_type == "daily_summary":
                # JSONB snapshot from midnight pre-compute (stable for full-day summary)
                calories_consumed = int(ctx.get("calories_consumed", 0))
            elif notif.notification_type.startswith("trial_expiry"):
                calories_consumed = 0
            elif notif.notification_type.startswith("hydration_reminder"):
                consumed_ml, goal_ml = hydration_map.get(notif.user_id, (0, 2000))
                threshold = 0.5 if "afternoon" in notif.notification_type else 0.8
                if consumed_ml >= threshold * goal_ml:
                    # User is on track — mark as sent without FCM
                    sent_ids.append(notif.id)
                    continue
                remaining_ml = max(0, goal_ml - consumed_ml)
                title, body = _render_message(
                    notif.notification_type,
                    0,
                    gender,
                    lang,
                    consumed_ml=consumed_ml,
                    goal_ml=goal_ml,
                    remaining_ml=remaining_ml,
                )
                group = groups[(notif.notification_type, title, body)]
                group["tokens"].extend(tokens)
                group["ids"].append(str(notif.id))
                sent_ids.append(notif.id)
                continue
            else:
                # meal_reminder_* — real-time DB data
                calories_consumed = consumed_map.get(notif.user_id, 0)

            remaining = max(0, calorie_goal - calories_consumed)
            title, body = _render_message(
                notif.notification_type,
                remaining,
                gender,
                lang,
                calories_consumed=calories_consumed,
                calorie_goal=calorie_goal,
            )
            group = groups[(notif.notification_type, title, body)]
            group["tokens"].extend(tokens)
            group["ids"].append(str(notif.id))
            sent_ids.append(notif.id)

        # Batch FCM — 500 tokens per call.
        # DB stores trial_expiry_2d / trial_expiry_1d so the UNIQUE
        # (user_id, type, scheduled_date) constraint dedups per-day; mobile expects
        # a single "trial_expiry" type in data.type for dispatch.
        for (notif_type, title, body), group in groups.items():
            fcm_type = (
                "trial_expiry" if notif_type.startswith("trial_expiry") else notif_type
            )
            data = {
                "notification_ids": ",".join(group["ids"]),
                "notification_count": str(len(group["ids"])),
            }
            tokens = group["tokens"]
            for chunk in _chunked(tokens, 500):
                result = self._firebase.send_multicast(
                    tokens=chunk,
                    title=title,
                    body=body,
                    notification_type=fcm_type,
                    data=data,
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
                    text("""
                        UPDATE notifications
                        SET status = 'sent'
                        WHERE status = 'processing' AND id IN :ids
                        """).bindparams(bindparam("ids", expanding=True)),
                    {"ids": sent_ids},
                )
            if failed_ids:
                uow.session.execute(
                    text("""
                        UPDATE notifications
                        SET status = 'failed'
                        WHERE status = 'processing' AND id IN :ids
                        """).bindparams(bindparam("ids", expanding=True)),
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
    consumed_ml: int = 0,
    goal_ml: int = 2000,
    remaining_ml: int = 0,
) -> tuple[str, str]:
    """Render title + body for a notification type. Title is empty for Time Sensitive."""
    messages = get_messages(lang, gender)
    if notification_type == "meal_reminder_breakfast":
        cfg = messages["meal_reminder"]["breakfast"]
        return "Nutree", cfg.get("body", "Time to log your meal 🍽️")
    elif notification_type == "meal_reminder_lunch":
        cfg = messages["meal_reminder"]["lunch"]
        return "Nutree", cfg["body_template"].format(remaining=remaining)
    elif notification_type == "meal_reminder_dinner":
        cfg = messages["meal_reminder"]["dinner"]
        return "Nutree", cfg["body_template"].format(remaining=remaining)
    elif notification_type == "daily_summary":
        summary = messages["daily_summary"]
        if calories_consumed == 0:
            return "Nutree", summary["zero_logs"]["body"]
        pct = (calories_consumed / calorie_goal * 100) if calorie_goal > 0 else 0
        if 95 <= pct <= 105:
            return "Nutree", summary["on_target"]["body_template"].format(
                percentage=int(pct)
            )
        elif pct < 95:
            return "Nutree", summary["under_goal"]["body_template"].format(
                deficit=int(calorie_goal - calories_consumed)
            )
        elif pct <= 120:
            return "Nutree", summary["slightly_over"]["body_template"].format(
                excess=int(calories_consumed - calorie_goal)
            )
        else:
            return "Nutree", summary["way_over"]["body_template"].format(
                excess=int(calories_consumed - calorie_goal)
            )
    elif notification_type.startswith("trial_expiry"):
        days = "2d" if notification_type.endswith("_2d") else "1d"
        trial = messages.get("trial_expiry", {}).get(days, {})
        return trial.get("title", "Nutree") or "Nutree", trial.get(
            "body", "Your trial is ending soon."
        )
    elif notification_type == "hydration_reminder_afternoon":
        cfg = messages["hydration_reminder"]["afternoon"]
        return "Nutree", cfg["body_template"].format(
            consumed_ml=consumed_ml, remaining_ml=remaining_ml
        )
    elif notification_type == "hydration_reminder_evening":
        cfg = messages["hydration_reminder"]["evening"]
        return "Nutree", cfg["body_template"].format(
            consumed_ml=consumed_ml, remaining_ml=remaining_ml
        )
    return "Nutree", "You have a notification 📬"


def _chunked(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def _fetch_calories_consumed_batch(
    user_ids: list[str], now: datetime
) -> dict[str, int]:
    """Batch-fetch calories consumed in the last 24 hours per user.

    Uses a 24-hour lookback from now. Meal reminders fire mid-day locally,
    so a 24-hour window captures all of the user's current-day meals.
    This replaces the Redis HGETALL that fetched a stale midnight snapshot.
    """
    window_start = now - timedelta(hours=24)
    with UnitOfWork() as uow:
        rows = uow.session.execute(
            text("""
                SELECT m.user_id,
                       COALESCE(SUM(
                           (n.protein * 4.0)
                           + (GREATEST(n.carbs - n.fiber, 0) * 4.0)
                           + (n.fiber * 2.0)
                           + (n.fat * 9.0)
                       ), 0) AS consumed_calories
                FROM meal m
                JOIN nutrition n ON n.meal_id = m.meal_id
                WHERE m.user_id = ANY(:ids)
                  AND m.created_at >= :start
                  AND m.status = 'READY'
                GROUP BY m.user_id
            """),
            {
                "ids": user_ids,
                "start": window_start,
            },
        ).fetchall()
    return {row.user_id: int(round(row.consumed_calories)) for row in rows}


def _fetch_hydration_data_batch(
    user_ids: list[str], now: datetime
) -> dict[str, tuple[int, int]]:
    """Fetch (consumed_ml, goal_ml) per user using a 24-hour rolling window.

    Uses a rolling 24h window consistent with _fetch_calories_consumed_batch.
    This is an approximation — a calendar-day boundary would be more accurate
    but requires per-user timezone joins. Acceptable for v1 threshold checks.
    """
    window_start = now - timedelta(hours=24)
    with UnitOfWork() as uow:
        profile_rows = uow.session.execute(
            text("""
                SELECT up.user_id, up.daily_water_goal_ml, up.weight_kg
                FROM user_profiles up
                WHERE up.user_id = ANY(:ids) AND up.is_current = true
            """),
            {"ids": user_ids},
        ).fetchall()

        profile_by_user = {r.user_id: r for r in profile_rows}

        hydration_rows = uow.session.execute(
            text("""
                SELECT user_id, COALESCE(SUM(credited_ml), 0) AS consumed_ml
                FROM hydration_logs
                WHERE user_id = ANY(:ids)
                  AND logged_at >= :start
                  AND is_deleted = false
                GROUP BY user_id
            """),
            {"ids": user_ids, "start": window_start},
        ).fetchall()

        consumed_by_user = {r.user_id: int(r.consumed_ml) for r in hydration_rows}

    result = {}
    for user_id in user_ids:
        profile = profile_by_user.get(user_id)
        if profile is None:
            result[user_id] = (0, 2000)
            continue
        weight = float(profile.weight_kg) if profile.weight_kg else 70.0
        goal_ml = profile.daily_water_goal_ml or round(35 * weight)
        consumed_ml = consumed_by_user.get(user_id, 0)
        result[user_id] = (consumed_ml, goal_ml)

    return result


def _seconds_until_next_minute(now: datetime) -> float:
    """Sleep until the next minute boundary without looking ahead."""
    seconds = now.second + (now.microsecond / 1_000_000)
    remaining = 60 - seconds
    if remaining <= 0 or remaining > 60:
        return float(ScheduledNotificationService.LOOP_INTERVAL_SECONDS)
    return remaining
