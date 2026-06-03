"""Scheduler that inserts a single trial-expiry push shortly before the trial
converts to paid, for the existing ScheduledNotificationService loop to send."""

import logging
import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.notification.notification import NotificationORM
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)

# Fire the reminder this long before the trial charges — a last-minute nudge
# so the user knows the charge is imminent.
_CHARGE_LEAD = timedelta(hours=2)
# Consider subscriptions charging within the next day; the row sits pending
# until its scheduled_for_utc, so a generous lookahead just means it is
# created early, never sent early.
_LOOKAHEAD_DAYS = 1


class ScheduledSubscriptionPushService:
    """Inserts one trial-expiry push per subscription, ~2h before its charge.

    Does not send. The existing ScheduledNotificationService loop polls
    `notifications` and sends due rows on its 60s tick.
    """

    def __init__(self) -> None:
        # Stateless; constructed once per process in main.py lifespan.
        pass

    def check_and_schedule_pushes(self, now: datetime | None = None) -> int:
        """Schedule the pre-charge push for subs charging soon. Returns rows
        inserted (excludes conflict-do-nothing skips)."""
        moment = now or utc_now()
        logger.info("Trial-push scheduler: starting run at %s", moment.isoformat())

        scheduled = self._schedule_due_pushes(moment)

        logger.info("Trial-push scheduler: complete, inserted=%s", scheduled)
        return scheduled

    # ---- scheduling pipeline --------------------------------------------

    def _schedule_due_pushes(self, now: datetime) -> int:
        with UnitOfWork() as uow:
            # Active subs whose trial converts to paid within the next day.
            subs = uow.subscriptions.find_expiring_in_window(
                from_days=0, to_days=_LOOKAHEAD_DAYS, now=now
            )
            if not subs:
                return 0

            user_ids = [s.user_id for s in subs]
            prefs = self._fetch_prefs(uow.session, user_ids)
            tokens_by_user = self._fetch_fcm_tokens(uow.session, user_ids)

            rows: list[dict] = []
            for sub in subs:
                tokens = tokens_by_user.get(sub.user_id, [])
                if not tokens:
                    continue
                row = self._build_row(
                    user_id=sub.user_id,
                    charge_at=sub.expires_at,
                    tokens=tokens,
                    pref=prefs.get(sub.user_id),
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
            text("""
                SELECT
                    np.user_id,
                    np.language,
                    u.timezone,
                    up.gender,
                    u.language_code
                FROM notification_preferences np
                JOIN users u ON u.id = np.user_id
                LEFT JOIN user_profiles up ON up.user_id = np.user_id AND up.is_current = true
                WHERE np.user_id = ANY(:ids) AND np.is_deleted = false
                """),
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
            text("""
                SELECT user_id, fcm_token
                FROM user_fcm_tokens
                WHERE user_id = ANY(:ids) AND is_active = true
                """),
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
        charge_at: datetime | None,
        tokens: list[str],
        pref: dict | None,
        now: datetime,
    ) -> dict | None:
        if charge_at is None or charge_at <= now:
            # No known charge moment, or the trial already converted — nothing
            # to warn about.
            return None

        tz_name = (pref or {}).get("timezone", "UTC")
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")

        # Fire shortly before the charge. If the sub only surfaced once we are
        # already inside that lead window (e.g. loop downtime), send on the next
        # tick — still before the charge.
        scheduled_utc = charge_at - _CHARGE_LEAD
        if scheduled_utc < now:
            scheduled_utc = now

        # Dedup date is pinned to the charge (stable per sub), so repeated ticks
        # and the clamp above never produce a second row for the same user.
        scheduled_local_date = charge_at.astimezone(tz).date()

        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            # "_1d" selects the single trial-expiry message variant; the suffix
            # is retained for dispatch routing and analytics continuity.
            "notification_type": "trial_expiry_1d",
            "scheduled_date": scheduled_local_date,
            "scheduled_for_utc": scheduled_utc,
            "status": "pending",
            "context": {
                "fcm_tokens": tokens,
                "calorie_goal": 2000,  # non-zero sentinel; trial render ignores it
                "calories_consumed": 0,
                "gender": (pref or {}).get("gender", "male"),
                "language_code": (pref or {}).get("language", "en"),
            },
            "created_at": utc_now(),
            "expires_at": scheduled_utc + timedelta(days=2),
        }

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
