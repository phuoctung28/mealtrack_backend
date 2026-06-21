"""Scheduler that inserts D1-D3 onboarding retention notification rows.

Does NOT send FCM — only inserts pending rows into the notifications table.
The cron dispatch phase claims and sends them.
"""

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.notification.notification import NotificationORM
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Campaign schedule definition
# Each tuple: (notification_type, campaign_day, local_hour, local_minute,
#              deeplink, display_mode, campaign_step)
# D3 premium_asset_lock timing is computed separately (_compute_asset_lock_at).
# ---------------------------------------------------------------------------

_D1_SLOTS = [
    ("d1_night_anchor", "1", 21, 0,
     "nutree://retention/mobility-intent", "mobility_modal", "night_anchor"),
]

_D2_SLOTS = [
    ("d2_morning_steps_sync", "2", 8, 30,
     "nutree://today-log/morning", "steps_sync", "morning_steps_sync"),
    ("d2_lunch_refuel", "2", 11, 45,
     "nutree://today-log", "fast_log", "lunch_refuel"),
    ("d2_hydration_slump", "2", 15, 0,
     "nutree://hydration", "hydration_charge", "hydration_slump"),
    ("d2_daily_summary", "2", 20, 0,
     "nutree://daily-summary", "summary", "daily_summary"),
]

_D3_FIXED_SLOTS = [
    ("d3_churn_preemption", "3", 9, 0,
     "nutree://progress-warning", "badge_prompt", "churn_preemption"),
]


# ---------------------------------------------------------------------------
# Module-level helper (imported by tests independently)
# ---------------------------------------------------------------------------


async def suppress_normal_daily_summary(session, user_id: str, local_date: date) -> int:
    """Delete pending daily_summary rows for this user/date.

    Only removes rows with status='pending' — sent/failed rows are preserved.
    Returns the count of deleted rows.
    """
    stmt = (
        delete(NotificationORM)
        .where(NotificationORM.user_id == user_id)
        .where(NotificationORM.notification_type == "daily_summary")
        .where(NotificationORM.scheduled_date == local_date)
        .where(NotificationORM.status == "pending")
    )
    result = await session.execute(stmt)
    return result.rowcount if (result.rowcount or 0) >= 0 else 0


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class OnboardingRetentionCampaignScheduler:
    """Insert pending D1-D3 retention notification rows for eligible users.

    Idempotent: ON CONFLICT DO NOTHING on (user_id, notification_type, scheduled_date).
    All campaign days are scheduled on every cron run; the unique constraint
    prevents duplicates so missed days are caught on the next run.
    """

    async def schedule(self, now: datetime) -> int:
        """Insert pending D1-D3 rows. Returns count of rows inserted."""
        logger.info("D1-D3 campaign scheduler: run at %s", now.isoformat())

        users = await self._fetch_eligible_users(now)
        if not users:
            logger.info("D1-D3 campaign scheduler: no eligible users")
            return 0

        user_ids = [u.user_id for u in users]
        states = await self._fetch_campaign_states(user_ids)

        rows = []
        # Tracks (user_id, d2_local_date) pairs needing normal summary suppression.
        d2_suppression_targets: list[tuple[str, date]] = []
        for user in users:
            tokens = list(user.fcm_tokens) if user.fcm_tokens else []
            if not tokens:
                continue
            state = states.get(user.user_id)
            if state is None:
                continue
            user_rows, d2_date = await self._build_rows_for_user(user, tokens, state, now)
            rows.extend(user_rows)
            if d2_date is not None:
                d2_suppression_targets.append((user.user_id, d2_date))

        if not rows:
            return 0

        async with AsyncUnitOfWork() as uow:
            inserted = await self._insert_rows(uow.session, rows)
            for uid, d2_date in d2_suppression_targets:
                await suppress_normal_daily_summary(uow.session, uid, d2_date)

        logger.info("D1-D3 campaign scheduler: inserted=%s", inserted)
        return inserted

    # -----------------------------------------------------------------------
    # Row construction per user
    # -----------------------------------------------------------------------

    async def _build_rows_for_user(
        self, user, tokens, state, now: datetime
    ) -> tuple[list, date | None]:
        """Build notification rows for one user. Returns (rows, d2_local_date_or_none).

        d2_local_date is returned when D2 slots are being scheduled so the caller
        can suppress the competing regular daily_summary row for that date.
        """
        tz = self._resolve_tz(user.timezone)
        started = state.campaign_started_at
        d1_local = started.astimezone(tz).date()
        d2_local = d1_local + timedelta(days=1)
        d3_local = d1_local + timedelta(days=2)
        today_local = now.astimezone(tz).date()

        rows = []
        d2_scheduled = None

        # Schedule D1 when we are on or after D1 local date
        if today_local >= d1_local:
            rows.extend(await self._build_fixed_slots(
                _D1_SLOTS, user, tokens, d1_local, tz, now, stale_check=True
            ))

        # Schedule D2 when we are on or after D2 local date
        if today_local >= d2_local:
            rows.extend(await self._build_fixed_slots(
                _D2_SLOTS, user, tokens, d2_local, tz, now, stale_check=False
            ))
            d2_scheduled = d2_local

        # Schedule D3 when we are on or after D3 local date
        if today_local >= d3_local:
            rows.extend(await self._build_fixed_slots(
                _D3_FIXED_SLOTS, user, tokens, d3_local, tz, now, stale_check=False
            ))
            asset_lock_row = await self._build_asset_lock_row(user, tokens, state, d3_local)
            if asset_lock_row:
                rows.append(asset_lock_row)

        return rows, d2_scheduled

    async def _build_fixed_slots(self, slots, user, tokens, local_date, tz, now, stale_check):
        rows = []
        for notif_type, campaign_day, hour, minute, deeplink, display_mode, step in slots:
            scheduled_utc = await self._local_time_to_utc(hour, minute, local_date, str(tz))
            if stale_check and now >= scheduled_utc:
                logger.debug("Skipping stale slot %s for user %s", notif_type, user.user_id)
                continue
            rows.append(self._make_row(
                user=user,
                tokens=tokens,
                notif_type=notif_type,
                campaign_day=campaign_day,
                step=step,
                deeplink=deeplink,
                display_mode=display_mode,
                local_date=local_date,
                scheduled_utc=scheduled_utc,
            ))
        return rows

    async def _build_asset_lock_row(self, user, tokens, state, d3_local):
        lock_at = await self._compute_asset_lock_at(
            campaign_started_at=state.campaign_started_at,
            subscription_expires_at=getattr(state, "subscription_expires_at", None),
        )
        return self._make_row(
            user=user,
            tokens=tokens,
            notif_type="d3_premium_asset_lock",
            campaign_day="3",
            step="premium_asset_lock",
            deeplink="nutree://premium/asset-lock",
            display_mode="premium_asset_lock",
            local_date=d3_local,
            scheduled_utc=lock_at,
        )

    def _make_row(self, user, tokens, notif_type, campaign_day, step,
                  deeplink, display_mode, local_date, scheduled_utc):
        return {
            "id": str(uuid.uuid4()),
            "user_id": user.user_id,
            "notification_type": notif_type,
            "scheduled_date": local_date,
            "scheduled_for_utc": scheduled_utc,
            "status": "pending",
            "context": {
                "fcm_tokens": tokens,
                "campaign": "onboarding_d1_d3",
                "campaign_day": campaign_day,
                "campaign_step": step,
                "deeplink": deeplink,
                "display_mode": display_mode,
                "language_code": getattr(user, "language", "en") or "en",
                "gender": getattr(user, "gender", "male") or "male",
            },
            "created_at": utc_now(),
            "expires_at": scheduled_utc + timedelta(days=2),
        }

    # -----------------------------------------------------------------------
    # DB fetch helpers — patched in tests via patch.object
    # -----------------------------------------------------------------------

    async def _fetch_eligible_users(self, now: datetime) -> list:
        """Return users whose campaign window started within the last 4 days."""
        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                text("""
                    SELECT
                        ors.user_id,
                        ors.campaign_started_at,
                        ors.campaign_timezone AS timezone,
                        u.language_code AS language,
                        up.gender,
                        array_agg(uft.fcm_token)
                            FILTER (WHERE uft.is_active = true) AS fcm_tokens
                    FROM onboarding_retention_states ors
                    JOIN users u ON u.id = ors.user_id
                    LEFT JOIN user_profiles up
                        ON up.user_id = ors.user_id AND up.is_current = true
                    LEFT JOIN user_fcm_tokens uft ON uft.user_id = ors.user_id
                    WHERE ors.campaign_started_at >= :cutoff
                    GROUP BY ors.user_id, ors.campaign_started_at,
                             ors.campaign_timezone, u.language_code, up.gender
                """),
                {"cutoff": now - timedelta(days=4)},
            )
            return result.fetchall()

    async def _fetch_campaign_states(self, user_ids: list) -> dict:
        """Return dict of user_id -> state row (includes subscription expires_at)."""
        if not user_ids:
            return {}
        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                text("""
                    SELECT
                        ors.user_id,
                        ors.campaign_started_at,
                        sub.expires_at AS subscription_expires_at
                    FROM onboarding_retention_states ors
                    LEFT JOIN subscriptions sub
                        ON sub.user_id = ors.user_id AND sub.status = 'active'
                    WHERE ors.user_id = ANY(:ids)
                """),
                {"ids": user_ids},
            )
            return {r.user_id: r for r in result.fetchall()}

    # -----------------------------------------------------------------------
    # Timing helpers — exposed as async for test patching
    # -----------------------------------------------------------------------

    async def _local_time_to_utc(
        self, local_hour: int, local_minute: int,
        local_date_utc, timezone: str
    ) -> datetime:
        """Convert local HH:MM on the calendar day of local_date_utc to UTC."""
        tz = self._resolve_tz(timezone)
        if isinstance(local_date_utc, datetime):
            cal_date = local_date_utc.astimezone(tz).date()
        else:
            cal_date = local_date_utc
        local_dt = datetime(
            cal_date.year, cal_date.month, cal_date.day,
            local_hour, local_minute, 0, tzinfo=tz,
        )
        return local_dt.astimezone(UTC)

    async def _compute_asset_lock_at(
        self, campaign_started_at: datetime, subscription_expires_at
    ) -> datetime:
        """UTC moment to fire the premium asset lock notification."""
        if subscription_expires_at is not None:
            return subscription_expires_at - timedelta(hours=6)
        return campaign_started_at + timedelta(hours=72) - timedelta(hours=6)

    # -----------------------------------------------------------------------
    # Insert — one row at a time for accurate rowcount tracking
    # -----------------------------------------------------------------------

    @staticmethod
    async def _insert_rows(session, rows: list) -> int:
        if not rows:
            return 0
        total = 0
        for row in rows:
            stmt = pg_insert(NotificationORM).values([row])
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["user_id", "notification_type", "scheduled_date"],
            )
            result = await session.execute(stmt)
            await session.flush()
            total += result.rowcount if (result.rowcount or 0) >= 0 else 0
        return total

    @staticmethod
    def _resolve_tz(tz_name) -> ZoneInfo:
        try:
            return ZoneInfo(tz_name or "UTC")
        except (ZoneInfoNotFoundError, Exception):
            return ZoneInfo("UTC")
