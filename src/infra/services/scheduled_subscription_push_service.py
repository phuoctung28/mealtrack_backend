"""Scheduler that inserts T-2d / T-1d trial-expiry push rows for the
existing ScheduledNotificationService loop to send."""

import logging
import uuid
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.notification.notification import NotificationORM
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)

_DEFAULT_LUNCH_MINUTES = 690    # 11:30 — mirrors daily_context_precompute_service
_FIRE_OFFSET_MINUTES = 30       # send at lunch + 30
_FALLBACK_FIRE_LOCAL = time(12, 0)  # if lunch_time_minutes missing → noon local


class ScheduledSubscriptionPushService:
    """Inserts trial-expiry push notifications at T-2d and T-1d.

    Does not send. The existing ScheduledNotificationService loop polls
    `notifications` and sends due rows on its 60s tick.
    """

    def __init__(self) -> None:
        # Stateless; constructed once per process in main.py lifespan.
        pass

    def check_and_schedule_pushes(self, now: datetime | None = None) -> int:
        """Run T-2d + T-1d windows. Returns total rows inserted (excludes
        conflict-do-nothing skips)."""
        moment = now or utc_now()
        logger.info("Trial-push scheduler: starting run at %s", moment.isoformat())

        scheduled = 0
        scheduled += self._schedule_window(moment, days_left=2)
        scheduled += self._schedule_window(moment, days_left=1)

        logger.info("Trial-push scheduler: complete, inserted=%s", scheduled)
        return scheduled

    # ---- window pipeline ------------------------------------------------

    def _schedule_window(self, now: datetime, days_left: int) -> int:
        with UnitOfWork() as uow:
            subs = uow.subscriptions.find_expiring_in_window(
                from_days=days_left, to_days=days_left + 1, now=now
            )
            if not subs:
                return 0

            user_ids = [s.user_id for s in subs]
            prefs = self._fetch_prefs(uow.session, user_ids)
            tokens_by_user = self._fetch_fcm_tokens(uow.session, user_ids)

            rows: list[dict] = []
            for sub in subs:
                pref = prefs.get(sub.user_id)
                tokens = tokens_by_user.get(sub.user_id, [])
                if not tokens:
                    continue
                row = self._build_row(
                    user_id=sub.user_id,
                    days_left=days_left,
                    tokens=tokens,
                    pref=pref,
                    now=now,
                )
                if row is not None:
                    rows.append(row)

            if not rows:
                return 0

            return self._insert_with_dedup(uow.session, rows)

    # ---- pref + token fetch (batch) -------------------------------------

    @staticmethod
    def _fetch_prefs(session, user_ids: list[str]) -> dict[str, dict]:
        if not user_ids:
            return {}
        result = session.execute(
            text(
                """
                SELECT
                    np.user_id,
                    np.lunch_time_minutes,
                    np.language,
                    u.timezone,
                    up.gender,
                    u.language_code
                FROM notification_preferences np
                JOIN users u ON u.id = np.user_id
                LEFT JOIN user_profiles up ON up.user_id = np.user_id AND up.is_current = true
                WHERE np.user_id = ANY(:ids) AND np.is_deleted = false
                """
            ),
            {"ids": user_ids},
        ).fetchall()

        def _resolve_lang(pref_lang, user_lang) -> str:
            # Matches daily_context_precompute_service.py:194
            if pref_lang in ("en", "vi"):
                return pref_lang
            if user_lang in ("en", "vi"):
                return user_lang
            return "en"

        return {
            r.user_id: {
                "lunch_time_minutes": r.lunch_time_minutes,
                "language": _resolve_lang(r.language, r.language_code),
                "timezone": r.timezone or "UTC",
                "gender": r.gender or "male",
            }
            for r in result
        }

    @staticmethod
    def _fetch_fcm_tokens(session, user_ids: list[str]) -> dict[str, list[str]]:
        if not user_ids:
            return {}
        result = session.execute(
            text(
                """
                SELECT user_id, fcm_token
                FROM user_fcm_tokens
                WHERE user_id = ANY(:ids) AND is_active = true
                """
            ),
            {"ids": user_ids},
        ).fetchall()
        tokens: dict[str, list[str]] = {}
        for r in result:
            tokens.setdefault(r.user_id, []).append(r.fcm_token)
        return tokens

    # ---- row construction -----------------------------------------------

    def _build_row(
        self,
        user_id: str,
        days_left: int,
        tokens: list[str],
        pref: dict | None,
        now: datetime,
    ) -> dict | None:
        tz_name = (pref or {}).get("timezone", "UTC")
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")

        scheduled_utc, scheduled_local_date = self._compute_scheduled_at(
            now_utc=now,
            tz=tz,
            lunch_time_minutes=(pref or {}).get("lunch_time_minutes"),
        )

        if scheduled_utc <= now:
            # Window already passed today in this tz — skip; tomorrow's
            # midnight run will pick it up if still in window.
            return None

        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "notification_type": f"trial_expiry_{days_left}d",
            "scheduled_date": scheduled_local_date,
            "scheduled_for_utc": scheduled_utc,
            "status": "pending",
            "context": {
                "fcm_tokens": tokens,
                "calorie_goal": 2000,    # non-zero sentinel; trial render ignores it
                "calories_consumed": 0,
                "gender": (pref or {}).get("gender", "male"),
                "language_code": (pref or {}).get("language", "en"),
            },
            "created_at": utc_now(),
            "expires_at": scheduled_utc + timedelta(days=2),
        }

    @staticmethod
    def _compute_scheduled_at(
        now_utc: datetime,
        tz: ZoneInfo,
        lunch_time_minutes: int | None,
    ) -> tuple[datetime, date]:
        """Returns (UTC datetime to fire at, local date the push fires)."""
        local_now = now_utc.astimezone(tz)
        local_today = local_now.date()

        if lunch_time_minutes is None:
            fire_local = datetime.combine(local_today, _FALLBACK_FIRE_LOCAL, tz)
        else:
            minutes = lunch_time_minutes + _FIRE_OFFSET_MINUTES
            hour, minute = divmod(minutes, 60)
            # Wrap to next day if lunch+30 overflows past midnight (extreme edge).
            extra_days, hour = divmod(hour, 24)
            fire_local = datetime.combine(
                local_today + timedelta(days=extra_days),
                time(hour, minute),
                tz,
            )

        return (
            fire_local.astimezone(now_utc.tzinfo or ZoneInfo("UTC")),
            fire_local.date(),
        )

    # ---- insert ----------------------------------------------------------

    @staticmethod
    def _insert_with_dedup(session, rows: Iterable[dict]) -> int:
        rows_list = list(rows)
        if not rows_list:
            return 0
        stmt = pg_insert(NotificationORM).values(rows_list)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["user_id", "notification_type", "scheduled_date"],
        )
        result = session.execute(stmt)
        # rowcount reflects rows actually inserted (excludes conflict skips).
        # Some drivers return -1 when count is unknown; treat as 0 for logging.
        return result.rowcount if (result.rowcount or 0) >= 0 else 0
