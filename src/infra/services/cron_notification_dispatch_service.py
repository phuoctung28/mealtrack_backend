"""Cron notification dispatch helper.

Cron push owns notification scheduling/precompute. This helper only claims due
notification rows, renders display text, sends FCM batches, and marks rows sent.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import and_, bindparam, or_, select, text

from src.domain.services.notification_messages import get_messages
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.notification.notification import NotificationORM
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)

DEACTIVATABLE_FCM_ERRORS = {
    "invalid-registration-token",
    "registration-token-not-registered",
    "NOT_FOUND",
    "UNREGISTERED",
    "INVALID_ARGUMENT",
    "UNAUTHENTICATED",
    "PERMISSION_DENIED",
}

PROCESSING_RECLAIM_AFTER = timedelta(minutes=10)


class CronNotificationDispatchService:
    """Batch-send notifications that cron has already scheduled."""

    # Rows claimed for sending sit in 'processing' only for one tick (seconds);
    # anything still 'processing' this long past its send time was abandoned.
    STALE_PROCESSING_MINUTES = 10

    def __init__(self, firebase_service: FirebaseService):
        self._firebase = firebase_service

    # ── Send due notifications ───────────────────────────────────────────────

    async def _send_due_notifications(self, now: datetime) -> None:
        """Fetch due rows, render messages, batch-send FCM, and mark sent."""

        # Recover rows stranded in 'processing' by a worker that died mid-send,
        # otherwise they would never be delivered.
        await self._recover_stale_processing()
        due = await self._claim_due_notifications(now)
        if not due:
            return

        logger.info("Sending %d claimed due notifications", len(due))

        # Batch-fetch real-time calories_consumed from DB for meal reminders.
        # daily_summary uses the JSONB snapshot; trial_expiry ignores calories.
        meal_reminder_ids = [
            n.user_id for n in due if n.notification_type.startswith("meal_reminder")
        ]
        consumed_map: dict[str, int] = {}
        if meal_reminder_ids:
            consumed_map = await _fetch_calories_consumed_batch(meal_reminder_ids, now)

        hydration_user_ids = [
            n.user_id
            for n in due
            if n.notification_type.startswith("hydration_reminder")
        ]
        hydration_map: dict[str, tuple[int, int]] = {}
        if hydration_user_ids:
            try:
                hydration_map = await _fetch_hydration_data_batch(
                    hydration_user_ids, now
                )
            except Exception as exc:
                logger.warning("Failed to fetch hydration data batch: %s", exc)

        # Render messages per notification and group by (type, title, body)
        groups: dict[tuple[str, str, str], dict[str, list]] = defaultdict(
            lambda: {"tokens": [], "ids": [], "row_ids": []}
        )
        sent_ids = []  # delivered (sent without FCM, or FCM batch confirmed success)
        failed_ids = []  # no usable tokens — give up
        retry_ids = []  # FCM batch failed wholesale — return to queue for next tick

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
                group["row_ids"].append(notif.id)
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
            group["row_ids"].append(notif.id)

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
            # A batch is delivered only if every chunk's FCM call succeeds. A
            # wholesale send failure (network/auth) returns success=False with no
            # failed_tokens; those rows must NOT be marked sent or they are lost
            # forever with zero delivery — return them to the queue to retry.
            group_delivered = True
            for chunk in _chunked(tokens, 500):
                result = self._firebase.send_multicast(
                    tokens=chunk,
                    title=title,
                    body=body,
                    notification_type=fcm_type,
                    data=data,
                )
                if not result.get("success"):
                    group_delivered = False
                if result.get("failed_tokens"):
                    await self._handle_failed_tokens(result["failed_tokens"])
            if group_delivered:
                sent_ids.extend(group["row_ids"])
            else:
                retry_ids.extend(group["row_ids"])

        # Mark sent / failed / retry
        if sent_ids or failed_ids or retry_ids:
            await self._mark_notifications(sent_ids, failed_ids, retry_ids)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _claim_due_notifications(self, now: datetime) -> list[NotificationORM]:
        """Claim pending due rows without blocking other cron workers."""
        status_filter = NotificationORM.status == "pending"
        stale_processing_before = now - PROCESSING_RECLAIM_AFTER
        status_filter = or_(
            status_filter,
            and_(
                NotificationORM.status == "processing",
                NotificationORM.scheduled_for_utc <= stale_processing_before,
            ),
        )

        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                select(NotificationORM)
                .where(
                    NotificationORM.scheduled_for_utc <= now,
                    status_filter,
                )
                .order_by(NotificationORM.scheduled_for_utc, NotificationORM.created_at)
                .with_for_update(skip_locked=True)
            )
            due_rows = list(result.scalars().all())
            for row in due_rows:
                row.status = "processing"
            await uow.session.flush()
            return due_rows

    async def _mark_notifications(
        self,
        sent_ids: list,
        failed_ids: list,
        retry_ids: list | None = None,
    ) -> None:
        async with AsyncUnitOfWork() as uow:
            if sent_ids:
                await uow.session.execute(
                    text("""
                        UPDATE notifications
                        SET status = 'sent'
                        WHERE status = 'processing' AND id IN :ids
                        """).bindparams(bindparam("ids", expanding=True)),
                    {"ids": sent_ids},
                )
            if failed_ids:
                await uow.session.execute(
                    text("""
                        UPDATE notifications
                        SET status = 'failed'
                        WHERE status = 'processing' AND id IN :ids
                        """).bindparams(bindparam("ids", expanding=True)),
                    {"ids": failed_ids},
                )
            if retry_ids:
                # FCM send failed wholesale — return rows to the queue so the next
                # cron tick re-claims and re-sends them instead of losing them.
                await uow.session.execute(
                    text("""
                        UPDATE notifications
                        SET status = 'pending'
                        WHERE status = 'processing' AND id IN :ids
                        """).bindparams(bindparam("ids", expanding=True)),
                    {"ids": retry_ids},
                )

    async def cleanup_expired_notifications(self) -> None:
        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                text("DELETE FROM notifications WHERE expires_at < NOW()")
            )
            logger.info("Cleaned up %d expired notification rows", result.rowcount)

    async def _recover_stale_processing(self) -> None:
        """Reset notifications stranded in 'processing' back to 'pending'.

        A row is set to 'processing' when claimed for sending; if the worker
        dies before marking it sent/failed it would otherwise stay 'processing'
        forever and never be delivered. Anything still 'processing' well past
        its scheduled time was abandoned by a dead worker.
        """
        cutoff = utc_now() - timedelta(minutes=self.STALE_PROCESSING_MINUTES)
        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                text("""
                    UPDATE notifications
                    SET status = 'pending'
                    WHERE status = 'processing' AND scheduled_for_utc < :cutoff
                    """),
                {"cutoff": cutoff},
            )
            if result.rowcount:
                logger.warning(
                    "Recovered %d stale 'processing' notifications → pending",
                    result.rowcount,
                )

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
            await self._deactivate_tokens(to_deactivate)

    async def _deactivate_tokens(self, tokens: list[str]) -> None:
        async with AsyncUnitOfWork() as uow:
            await uow.session.execute(
                text("""
                    UPDATE user_fcm_tokens
                    SET is_active = false
                    WHERE fcm_token IN :tokens
                    """).bindparams(bindparam("tokens", expanding=True)),
                {"tokens": tokens},
            )


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
    """Render non-empty title + body for a notification type."""
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


async def _fetch_calories_consumed_batch(
    user_ids: list[str], now: datetime
) -> dict[str, int]:
    """Batch-fetch calories consumed in the last 24 hours per user.

    Uses a 24-hour lookback from now. Meal reminders fire mid-day locally,
    so a 24-hour window captures all of the user's current-day meals.
    This replaces the Redis HGETALL that fetched a stale midnight snapshot.
    """
    window_start = now - timedelta(hours=24)
    async with AsyncUnitOfWork() as uow:
        result = await uow.session.execute(
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
        )
        rows = result.fetchall()
    return {row.user_id: int(round(row.consumed_calories)) for row in rows}


async def _fetch_hydration_data_batch(
    user_ids: list[str], now: datetime
) -> dict[str, tuple[int, int]]:
    """Fetch (consumed_ml, goal_ml) per user using a 24-hour rolling window.

    Uses a rolling 24h window consistent with _fetch_calories_consumed_batch.
    This is an approximation — a calendar-day boundary would be more accurate
    but requires per-user timezone joins. Acceptable for v1 threshold checks.
    """
    window_start = now - timedelta(hours=24)
    async with AsyncUnitOfWork() as uow:
        profile_result = await uow.session.execute(
            text("""
                SELECT up.user_id, up.daily_water_goal_ml, up.weight_kg
                FROM user_profiles up
                WHERE up.user_id = ANY(:ids) AND up.is_current = true
            """),
            {"ids": user_ids},
        )
        profile_rows = profile_result.fetchall()

        profile_by_user = {r.user_id: r for r in profile_rows}

        hydration_result = await uow.session.execute(
            text("""
                SELECT user_id, COALESCE(SUM(quantity), 0) AS consumed_ml
                FROM meal
                WHERE user_id = ANY(:ids)
                  AND meal_type = 'hydration'
                  AND created_at >= :start
                  AND status != 'INACTIVE'
                GROUP BY user_id
            """),
            {"ids": user_ids, "start": window_start},
        )
        hydration_rows = hydration_result.fetchall()

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
