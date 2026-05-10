"""Batch pre-compute user notification context per timezone group."""

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.domain.services.meal_suggestion.suggestion_tdee_helpers import (
    build_tdee_request,
)
from src.domain.services.tdee_service import TdeeCalculationService
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.redis_client import RedisClient
from src.infra.database.models.notification.notification import NotificationORM
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)

_CONTEXT_TTL = 86_400  # 24 h
_SENTINEL_TTL = 25 * 3_600  # 25 h — survives the full day
_NOTIF_EXPIRY_DAYS = 7

_DEFAULT_BREAKFAST_MINUTES = 510  # 08:30
_DEFAULT_LUNCH_MINUTES = 690  # 11:30
_DEFAULT_DINNER_MINUTES = 1_080  # 18:00
_DEFAULT_SUMMARY_MINUTES = 1_260  # 21:00


class DailyContextPrecomputeService:
    """Pre-computes calorie_goal, calories_consumed, gender, language per user at timezone midnight."""

    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client
        self._tdee_service = TdeeCalculationService()
        self._locks: dict[str, asyncio.Lock] = {}

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    def sentinel_key(self, today: date, tz_name: str) -> str:
        return f"precomputed:{today.isoformat()}:{tz_name}"

    def context_key(self, user_id: str) -> str:
        return f"user_daily_context:{user_id}"

    # ------------------------------------------------------------------
    # Public async entry point
    # ------------------------------------------------------------------

    async def is_precomputed(self, today: date, tz_name: str) -> bool:
        return await self._redis.exists(self.sentinel_key(today, tz_name))

    async def precompute_for_timezone(self, tz_name: str, today: date) -> None:
        """No-op if sentinel exists; otherwise runs DB sync work in thread pool."""
        # Fast path — sentinel already set (common case once run each day)
        if await self.is_precomputed(today, tz_name):
            logger.debug(
                "Pre-compute sentinel hit for %s on %s — skipping", tz_name, today
            )
            return

        # Serialize concurrent callers for the same (date, tz) pair. Startup catch-up
        # and the midnight loop tick can overlap; lock + recheck prevents double execution.
        lock_key = f"{today.isoformat()}:{tz_name}"
        if lock_key not in self._locks:
            self._locks[lock_key] = asyncio.Lock()
        async with self._locks[lock_key]:
            if await self.is_precomputed(today, tz_name):
                logger.debug(
                    "Pre-compute sentinel hit for %s on %s — skipping", tz_name, today
                )
                return

            logger.debug(
                "Pre-computing notification context for %s on %s", tz_name, today
            )
            redis_items = await asyncio.to_thread(
                self._precompute_db_sync, tz_name, today
            )

            if redis_items:
                ok = await self._redis.hset_batch(redis_items)
                if not ok:
                    logger.error(
                        "hset_batch failed for %s — sentinel will NOT be set, retry next tick",
                        tz_name,
                    )
                    return

            await self._redis.set(
                self.sentinel_key(today, tz_name), "1", ttl=_SENTINEL_TTL
            )
            logger.debug(
                "Pre-compute complete for %s: %d users", tz_name, len(redis_items)
            )

    async def reschedule_user_notifications(self, user_id: str) -> int:
        """Reschedule notifications for a single user after preferences update.

        Deletes pending notifications for today and creates new ones with updated times.
        Returns number of notifications scheduled.
        """
        return await asyncio.to_thread(self._reschedule_user_sync, user_id)

    def _reschedule_user_sync(self, user_id: str) -> int:
        """Sync implementation of user notification rescheduling."""
        with UnitOfWork() as uow:
            session = uow.session

            # Get user's timezone
            user_row = session.execute(
                text("SELECT timezone FROM users WHERE id = :user_id AND is_active = true"),
                {"user_id": user_id},
            ).fetchone()

            if not user_row or not user_row.timezone:
                logger.warning("Cannot reschedule: user %s has no timezone", user_id)
                return 0

            tz_name = user_row.timezone
            try:
                tz = ZoneInfo(tz_name)
            except ZoneInfoNotFoundError:
                tz = ZoneInfo("UTC")
                tz_name = "UTC"

            today = datetime.now(tz).date()

            # Delete existing pending notifications for today
            session.execute(
                text("""
                    DELETE FROM notifications
                    WHERE user_id = :user_id
                      AND scheduled_date = :today
                      AND status = 'pending'
                """),
                {"user_id": user_id, "today": today},
            )

            # Get user's notification preferences
            pref_row = session.execute(
                text("""
                    SELECT meal_reminders_enabled, daily_summary_enabled,
                           breakfast_time_minutes, lunch_time_minutes,
                           dinner_time_minutes, daily_summary_time_minutes, language
                    FROM notification_preferences
                    WHERE user_id = :user_id AND is_deleted = false
                """),
                {"user_id": user_id},
            ).fetchone()

            if not pref_row:
                logger.info("No notification preferences for user %s", user_id)
                return 0

            # Get active FCM tokens
            token_rows = session.execute(
                text("""
                    SELECT fcm_token FROM user_fcm_tokens
                    WHERE user_id = :user_id AND is_active = true
                """),
                {"user_id": user_id},
            ).fetchall()

            tokens = [row.fcm_token for row in token_rows]
            if not tokens:
                logger.info("No active FCM tokens for user %s", user_id)
                return 0

            # Get profile for gender and calorie goal
            profile_row = session.execute(
                text("""
                    SELECT up.gender, u.language_code
                    FROM user_profiles up
                    JOIN users u ON u.id = up.user_id
                    WHERE up.user_id = :user_id AND up.is_current = true
                """),
                {"user_id": user_id},
            ).fetchone()

            gender = (profile_row.gender if profile_row else None) or "male"
            language_code = pref_row.language or (profile_row.language_code if profile_row else "en") or "en"

            # Calculate calorie goal (simplified - use TDEE service for accuracy)
            calorie_goal = self._get_user_calorie_goal(session, user_id)

            # Get today's consumed calories
            day_start_utc = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=tz).astimezone(timezone.utc)
            day_end_utc = day_start_utc + timedelta(days=1)

            consumed_row = session.execute(
                text("""
                    SELECT COALESCE(SUM(
                        protein * 4 + (carbs - COALESCE(fiber, 0)) * 4 +
                        COALESCE(fiber, 0) * 2 + fat * 9
                    ), 0) as total
                    FROM meal_logs
                    WHERE user_id = :user_id
                      AND logged_at >= :start AND logged_at < :end
                      AND is_deleted = false
                """),
                {"user_id": user_id, "start": day_start_utc, "end": day_end_utc},
            ).fetchone()

            calories_consumed = int(round(consumed_row.total)) if consumed_row else 0

            # Build notification rows
            context = {
                "fcm_tokens": tokens,
                "calorie_goal": calorie_goal,
                "calories_consumed": calories_consumed,
                "gender": gender,
                "language_code": language_code,
            }

            now = utc_now()
            expires_at = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) + timedelta(days=_NOTIF_EXPIRY_DAYS)
            rows = []

            if pref_row.meal_reminders_enabled:
                for notif_type, local_minutes in [
                    ("meal_reminder_breakfast", pref_row.breakfast_time_minutes or _DEFAULT_BREAKFAST_MINUTES),
                    ("meal_reminder_lunch", pref_row.lunch_time_minutes or _DEFAULT_LUNCH_MINUTES),
                    ("meal_reminder_dinner", pref_row.dinner_time_minutes or _DEFAULT_DINNER_MINUTES),
                ]:
                    scheduled_utc = _local_minutes_to_utc(today, local_minutes, tz_name)
                    if scheduled_utc and scheduled_utc > now:  # Only schedule future notifications
                        rows.append({
                            "id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "notification_type": notif_type,
                            "scheduled_date": today,
                            "scheduled_for_utc": scheduled_utc,
                            "status": "pending",
                            "context": context,
                            "created_at": now,
                            "expires_at": expires_at,
                        })

            if pref_row.daily_summary_enabled:
                summary_minutes = pref_row.daily_summary_time_minutes or _DEFAULT_SUMMARY_MINUTES
                scheduled_utc = _local_minutes_to_utc(today, summary_minutes, tz_name)
                if scheduled_utc and scheduled_utc > now:
                    rows.append({
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "notification_type": "daily_summary",
                        "scheduled_date": today,
                        "scheduled_for_utc": scheduled_utc,
                        "status": "pending",
                        "context": context,
                        "created_at": now,
                        "expires_at": expires_at,
                    })

            # Insert new notifications
            if rows:
                stmt = pg_insert(NotificationORM).values(rows)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["user_id", "notification_type", "scheduled_date"]
                )
                session.execute(stmt)

            logger.info("Rescheduled %d notifications for user %s", len(rows), user_id)
            return len(rows)

    def _get_user_calorie_goal(self, session, user_id: str) -> int:
        """Get user's daily calorie goal from weekly budget or TDEE."""
        # Try weekly budget first
        budget_row = session.execute(
            text("""
                SELECT adjusted_daily_calories FROM weekly_budgets
                WHERE user_id = :user_id AND is_active = true
                ORDER BY week_start_date DESC LIMIT 1
            """),
            {"user_id": user_id},
        ).fetchone()

        if budget_row and budget_row.adjusted_daily_calories:
            return int(budget_row.adjusted_daily_calories)

        # Fallback to TDEE calculation
        profile_row = session.execute(
            text("""
                SELECT age, gender, height_cm, weight_kg, body_fat_percentage,
                       job_type, training_days_per_week, training_minutes_per_session,
                       fitness_goal, training_level
                FROM user_profiles
                WHERE user_id = :user_id AND is_current = true
            """),
            {"user_id": user_id},
        ).fetchone()

        if not profile_row:
            return 2000  # Default fallback

        try:
            tdee_request = build_tdee_request(profile_row)
            result = self._tdee_service.calculate_tdee(tdee_request)
            return int(result.adjusted_tdee)
        except Exception:
            return 2000

    # ------------------------------------------------------------------
    # Synchronous DB work (runs in thread pool via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _precompute_db_sync(
        self, tz_name: str, today: date
    ) -> list[tuple[str, dict, int]]:
        """
        All DB work: 5 SQL queries + 1 bulk INSERT.
        Returns list of (redis_key, mapping, ttl) for async Redis batch write.
        """
        with UnitOfWork() as uow:
            session = uow.session

            # ---- Query 1: users in this timezone with notification prefs ----
            pref_rows = session.execute(
                text("""
                    SELECT
                        np.user_id,
                        np.meal_reminders_enabled,
                        np.daily_summary_enabled,
                        np.breakfast_time_minutes,
                        np.lunch_time_minutes,
                        np.dinner_time_minutes,
                        np.daily_summary_time_minutes,
                        np.language
                    FROM notification_preferences np
                    JOIN users u ON u.id = np.user_id
                    WHERE u.timezone = :tz_name
                      AND u.is_active = true
                      AND np.is_deleted = false
                """),
                {"tz_name": tz_name},
            ).fetchall()

            if not pref_rows:
                return []

            user_ids = [row.user_id for row in pref_rows]

            # ---- Query 2: active FCM tokens for all users ----
            token_rows = session.execute(
                text("""
                    SELECT user_id, fcm_token
                    FROM user_fcm_tokens
                    WHERE user_id = ANY(:ids)
                      AND is_active = true
                """),
                {"ids": user_ids},
            ).fetchall()

            tokens_by_user: dict[str, list[str]] = defaultdict(list)
            for row in token_rows:
                tokens_by_user[row.user_id].append(row.fcm_token)

            # ---- Query 3: current user profiles ----
            profile_rows = session.execute(
                text("""
                    SELECT
                        up.user_id,
                        up.age,
                        up.gender,
                        up.height_cm,
                        up.weight_kg,
                        up.body_fat_percentage,
                        up.job_type,
                        up.training_days_per_week,
                        up.training_minutes_per_session,
                        up.fitness_goal,
                        up.training_level,
                        u.language_code
                    FROM user_profiles up
                    JOIN users u ON u.id = up.user_id
                    WHERE up.user_id = ANY(:ids)
                      AND up.is_current = true
                """),
                {"ids": user_ids},
            ).fetchall()

            profiles_by_user = {row.user_id: row for row in profile_rows}

            # ---- Query 4: calories consumed today per user ----
            # Compute UTC window for today in this timezone
            try:
                tz = ZoneInfo(tz_name)
            except ZoneInfoNotFoundError:
                tz = ZoneInfo("UTC")

            day_start_utc = datetime(
                today.year, today.month, today.day, 0, 0, 0, tzinfo=tz
            ).astimezone(timezone.utc)
            day_end_utc = day_start_utc + timedelta(days=1)

            # Calories: P*4 + (C-fiber)*4 + fiber*2 + F*9 (canonical formula per CLAUDE.md)
            consumed_rows = session.execute(
                text("""
                    SELECT
                        m.user_id,
                        COALESCE(
                            SUM(
                                (n.protein * 4.0)
                                + (GREATEST(n.carbs - n.fiber, 0) * 4.0)
                                + (n.fiber * 2.0)
                                + (n.fat * 9.0)
                            ),
                            0
                        ) AS consumed_calories
                    FROM meal m
                    JOIN nutrition n ON n.meal_id = m.meal_id
                    WHERE m.user_id = ANY(:ids)
                      AND m.created_at >= :start
                      AND m.created_at < :end
                      AND m.status = 'READY'
                    GROUP BY m.user_id
                """),
                {
                    "ids": user_ids,
                    "start": day_start_utc.replace(tzinfo=None),
                    "end": day_end_utc.replace(tzinfo=None),
                },
            ).fetchall()

            consumed_by_user: dict[str, float] = {
                row.user_id: float(row.consumed_calories) for row in consumed_rows
            }

            # ---- Compute calorie goals via TDEE (per user, with fallback) ----
            calorie_goals: dict[str, int] = {}
            for user_id in user_ids:
                profile = profiles_by_user.get(user_id)
                if profile is None:
                    calorie_goals[user_id] = 2000
                    continue
                try:
                    tdee_req = build_tdee_request(profile)
                    tdee_resp = self._tdee_service.calculate_tdee(tdee_req)
                    calorie_goals[user_id] = int(round(tdee_resp.macros.calories))
                except Exception as exc:
                    logger.warning(
                        "TDEE calculation failed for user %s: %s — using 2000 kcal fallback",
                        user_id,
                        exc,
                    )
                    calorie_goals[user_id] = 2000

            # ---- Query 5 / bulk INSERT: pre-build notification rows ----
            notif_rows = self._build_notification_rows(
                pref_rows=pref_rows,
                tokens_by_user=tokens_by_user,
                calorie_goals=calorie_goals,
                consumed_by_user=consumed_by_user,
                profiles_by_user=profiles_by_user,
                today=today,
                tz_name=tz_name,
            )

            if notif_rows:
                stmt = pg_insert(NotificationORM).values(notif_rows)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["user_id", "notification_type", "scheduled_date"],
                )
                session.execute(stmt)

            # ---- Build Redis items ----
            redis_items: list[tuple[str, dict, int]] = []
            for pref_row in pref_rows:
                user_id = pref_row.user_id
                profile = profiles_by_user.get(user_id)
                gender = (profile.gender if profile else None) or "male"
                language_code = pref_row.language or "en"

                mapping = {
                    "calorie_goal": str(calorie_goals.get(user_id, 2000)),
                    "calories_consumed": str(
                        int(round(consumed_by_user.get(user_id, 0.0)))
                    ),
                    "gender": gender,
                    "language_code": language_code,
                }
                redis_items.append((self.context_key(user_id), mapping, _CONTEXT_TTL))

            return redis_items

    # ------------------------------------------------------------------
    # Notification row builder
    # ------------------------------------------------------------------

    def _build_notification_rows(
        self,
        pref_rows,
        tokens_by_user: dict,
        calorie_goals: dict,
        consumed_by_user: dict,
        profiles_by_user: dict,
        today: date,
        tz_name: str,
    ) -> list[dict]:
        """Build list of dicts for bulk INSERT into notifications table."""
        now = utc_now()
        expires_at = datetime(
            today.year, today.month, today.day, tzinfo=timezone.utc
        ) + timedelta(days=_NOTIF_EXPIRY_DAYS)

        rows = []
        for pref in pref_rows:
            user_id = pref.user_id
            tokens = tokens_by_user.get(user_id, [])
            if not tokens:
                continue

            calorie_goal = calorie_goals.get(user_id, 2000)
            profile = profiles_by_user.get(user_id)
            gender = (profile.gender if profile else None) or "male"
            language_code = pref.language or "en"

            context = {
                "fcm_tokens": tokens,
                "calorie_goal": calorie_goal,
                "calories_consumed": int(round(consumed_by_user.get(user_id, 0.0))),
                "gender": gender,
                "language_code": language_code,
            }

            if pref.meal_reminders_enabled:
                for notif_type, local_minutes in [
                    (
                        "meal_reminder_breakfast",
                        pref.breakfast_time_minutes or _DEFAULT_BREAKFAST_MINUTES,
                    ),
                    (
                        "meal_reminder_lunch",
                        pref.lunch_time_minutes or _DEFAULT_LUNCH_MINUTES,
                    ),
                    (
                        "meal_reminder_dinner",
                        pref.dinner_time_minutes or _DEFAULT_DINNER_MINUTES,
                    ),
                ]:
                    scheduled_utc = _local_minutes_to_utc(today, local_minutes, tz_name)
                    if scheduled_utc is None:
                        continue
                    rows.append(
                        {
                            "id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "notification_type": notif_type,
                            "scheduled_date": today,
                            "scheduled_for_utc": scheduled_utc,
                            "status": "pending",
                            "context": context,
                            "created_at": now,
                            "expires_at": expires_at,
                        }
                    )

            if pref.daily_summary_enabled:
                summary_minutes = (
                    pref.daily_summary_time_minutes or _DEFAULT_SUMMARY_MINUTES
                )
                scheduled_utc = _local_minutes_to_utc(today, summary_minutes, tz_name)
                if scheduled_utc is not None:
                    rows.append(
                        {
                            "id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "notification_type": "daily_summary",
                            "scheduled_date": today,
                            "scheduled_for_utc": scheduled_utc,
                            "status": "pending",
                            "context": context,
                            "created_at": now,
                            "expires_at": expires_at,
                        }
                    )

        return rows


def _local_minutes_to_utc(local_date: date, local_minutes: int, tz_name: str):
    """Convert local time (minutes from midnight) on local_date to UTC datetime (timezone-aware)."""
    try:
        tz = ZoneInfo(tz_name)
        local_dt = datetime(
            local_date.year,
            local_date.month,
            local_date.day,
            local_minutes // 60,
            local_minutes % 60,
            0,
            tzinfo=tz,
        )
        return local_dt.astimezone(timezone.utc)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        logger.warning(
            "Cannot compute UTC for tz=%s minutes=%d: %s", tz_name, local_minutes, exc
        )
        return None
