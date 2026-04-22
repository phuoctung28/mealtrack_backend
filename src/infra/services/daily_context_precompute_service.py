"""Batch pre-compute user notification context per timezone group."""
import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text

from src.domain.services.meal_suggestion.suggestion_tdee_helpers import build_tdee_request
from src.domain.services.tdee_service import TdeeCalculationService
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.redis_client import RedisClient
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)

_CONTEXT_TTL = 86_400       # 24 h
_SENTINEL_TTL = 25 * 3_600  # 25 h — survives the full day
_NOTIF_EXPIRY_DAYS = 7

_DEFAULT_BREAKFAST_MINUTES = 480   # 08:00
_DEFAULT_LUNCH_MINUTES = 720       # 12:00
_DEFAULT_DINNER_MINUTES = 1_080    # 18:00
_DEFAULT_SUMMARY_MINUTES = 1_260   # 21:00


class DailyContextPrecomputeService:
    """Pre-computes calorie_goal, calories_consumed, gender, language per user at timezone midnight."""

    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client
        self._tdee_service = TdeeCalculationService()

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
        if await self.is_precomputed(today, tz_name):
            logger.debug("Pre-compute sentinel hit for %s on %s — skipping", tz_name, today)
            return

        logger.info("Pre-computing notification context for %s on %s", tz_name, today)
        redis_items = await asyncio.to_thread(self._precompute_db_sync, tz_name, today)

        if redis_items:
            await self._redis.hset_batch(redis_items)

        await self._redis.set(self.sentinel_key(today, tz_name), "1", ttl=_SENTINEL_TTL)
        logger.info("Pre-compute complete for %s: %d users", tz_name, len(redis_items))

    # ------------------------------------------------------------------
    # Synchronous DB work (runs in thread pool via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _precompute_db_sync(self, tz_name: str, today: date) -> list[tuple[str, dict, int]]:
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

            # Calories derived: P*4 + C*4 + F*9 (approximate for notification display)
            consumed_rows = session.execute(
                text("""
                    SELECT
                        m.user_id,
                        COALESCE(
                            SUM((n.protein * 4.0) + (n.carbs * 4.0) + (n.fat * 9.0)),
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
                row.user_id: float(row.consumed_calories)
                for row in consumed_rows
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
                profiles_by_user=profiles_by_user,
                today=today,
                tz_name=tz_name,
            )

            if notif_rows:
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                from src.infra.database.models.notification.notification import NotificationORM

                stmt = pg_insert(NotificationORM).values(notif_rows)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["user_id", "notification_type", "scheduled_date"],
                )
                session.execute(stmt)
                session.commit()

            # ---- Build Redis items ----
            redis_items: list[tuple[str, dict, int]] = []
            for pref_row in pref_rows:
                user_id = pref_row.user_id
                profile = profiles_by_user.get(user_id)
                gender = (profile.gender if profile else None) or "male"
                language_code = pref_row.language or "en"

                mapping = {
                    "calorie_goal": str(calorie_goals.get(user_id, 2000)),
                    "calories_consumed": str(int(round(consumed_by_user.get(user_id, 0.0)))),
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
                "gender": gender,
                "language_code": language_code,
            }

            if pref.meal_reminders_enabled:
                for notif_type, local_minutes in [
                    ("meal_reminder_breakfast", pref.breakfast_time_minutes or _DEFAULT_BREAKFAST_MINUTES),
                    ("meal_reminder_lunch", pref.lunch_time_minutes or _DEFAULT_LUNCH_MINUTES),
                    ("meal_reminder_dinner", pref.dinner_time_minutes or _DEFAULT_DINNER_MINUTES),
                ]:
                    scheduled_utc = _local_minutes_to_utc(today, local_minutes, tz_name)
                    if scheduled_utc is None:
                        continue
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

            if pref.daily_summary_enabled:
                summary_minutes = pref.daily_summary_time_minutes or _DEFAULT_SUMMARY_MINUTES
                scheduled_utc = _local_minutes_to_utc(today, summary_minutes, tz_name)
                if scheduled_utc is not None:
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

        return rows


def _local_minutes_to_utc(local_date: date, local_minutes: int, tz_name: str):
    """Convert local time (minutes from midnight) on local_date to UTC datetime (timezone-aware)."""
    try:
        tz = ZoneInfo(tz_name)
        local_dt = datetime(
            local_date.year, local_date.month, local_date.day,
            local_minutes // 60, local_minutes % 60, 0,
            tzinfo=tz,
        )
        return local_dt.astimezone(timezone.utc)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        logger.warning(
            "Cannot compute UTC for tz=%s minutes=%d: %s", tz_name, local_minutes, exc
        )
        return None
