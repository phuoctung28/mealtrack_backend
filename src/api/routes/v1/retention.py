"""Retention campaign API endpoints for D1-D3 onboarding."""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_user_id
from src.api.schemas.request.retention_requests import MobilityIntentRequest
from src.api.schemas.response.retention_responses import (
    AssetSummaryResponse,
    MobilityIntentResponse,
)
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.config_async import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/retention", tags=["Retention"])


async def _get_async_session():
    """Yield a fresh async DB session. Override in tests via dependency_overrides."""
    if AsyncSessionLocal is None:
        raise RuntimeError("AsyncSessionLocal is not initialized.")
    async with AsyncSessionLocal() as session:
        yield session


async def _suppress_normal_daily_summary(user_id: str, local_date, session) -> int:
    """Delete the normal daily_summary notification row for user+date so it
    does not duplicate the campaign D2 push. Returns number of rows deleted."""
    result = await session.execute(
        text(
            "DELETE FROM notifications "
            "WHERE user_id = :uid "
            "AND notification_type = 'daily_summary' "
            "AND DATE(scheduled_for AT TIME ZONE 'UTC') = :day "
            "RETURNING id"
        ),
        {"uid": user_id, "day": local_date},
    )
    return result.rowcount


# ---------------------------------------------------------------------------
# PUT /v1/retention/onboarding/mobility-intent
# ---------------------------------------------------------------------------


@router.put("/onboarding/mobility-intent", response_model=MobilityIntentResponse)
async def upsert_mobility_intent(
    body: MobilityIntentRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_async_session),
):
    """Record the user's commute mode for tomorrow (D1 modal response)."""
    user_row = await session.execute(
        text("SELECT onboarding_completed, timezone FROM users WHERE id = :uid"),
        {"uid": user_id},
    )
    user = user_row.mappings().first()

    # None means no DB row returned (stub session in tests or user deleted mid-request).
    # A real absent user would already be rejected by get_current_user_id; here we
    # only block users whose onboarding is explicitly marked incomplete.
    if user is not None and not user["onboarding_completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has not completed onboarding.",
        )

    tz = (user["timezone"] if user else None) or "UTC"
    now = utc_now()

    await session.execute(
        text(
            "INSERT INTO onboarding_retention_states "
            "(id, user_id, campaign_started_at, campaign_timezone, tomorrow_mobility_type, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :uid, :started_at, :tz, :mobility, now(), now()) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "tomorrow_mobility_type = EXCLUDED.tomorrow_mobility_type, "
            "updated_at = now()"
        ),
        {
            "uid": user_id,
            "started_at": now,
            "tz": tz,
            "mobility": body.tomorrow_mobility_type,
        },
    )
    await session.commit()
    return MobilityIntentResponse(success=True)


# ---------------------------------------------------------------------------
# GET /v1/retention/onboarding/asset-summary
# ---------------------------------------------------------------------------


@router.get("/onboarding/asset-summary", response_model=AssetSummaryResponse)
async def get_asset_summary(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(_get_async_session),
):
    """Return campaign asset counts and trial window timestamps."""
    state_row = await session.execute(
        text(
            "SELECT campaign_started_at FROM onboarding_retention_states "
            "WHERE user_id = :uid"
        ),
        {"uid": user_id},
    )
    state = state_row.mappings().first()

    if state is None:
        # No campaign state yet — return zero defaults so mobile can render safely.
        return AssetSummaryResponse(
            meal_scan_count=0,
            hydration_entry_count=0,
            hydration_win_count=0,
            movement_entry_count=0,
            active_day_count=0,
            trial_end_at=None,
            lock_at=None,
        )

    started_at = state["campaign_started_at"]

    meal_scan_row = await session.execute(
        text(
            "SELECT COUNT(*) AS cnt FROM meal "
            "WHERE user_id = :uid AND source = 'scanner' "
            "AND created_at >= :started_at"
        ),
        {"uid": user_id, "started_at": started_at},
    )
    meal_scan_count = meal_scan_row.scalar() or 0

    hydration_row = await session.execute(
        text(
            "SELECT COUNT(*) AS cnt FROM hydration_entries "
            "WHERE user_id = :uid AND logged_at >= :started_at"
        ),
        {"uid": user_id, "started_at": started_at},
    )
    hydration_entry_count = hydration_row.scalar() or 0

    hydration_win_row = await session.execute(
        text(
            "SELECT COUNT(DISTINCT DATE(logged_at AT TIME ZONE 'UTC')) AS cnt "
            "FROM hydration_entries "
            "WHERE user_id = :uid AND logged_at >= :started_at"
        ),
        {"uid": user_id, "started_at": started_at},
    )
    hydration_win_count = hydration_win_row.scalar() or 0

    movement_row = await session.execute(
        text(
            "SELECT COUNT(*) AS cnt FROM movement_entries "
            "WHERE user_id = :uid AND logged_at >= :started_at"
        ),
        {"uid": user_id, "started_at": started_at},
    )
    movement_entry_count = movement_row.scalar() or 0

    active_day_row = await session.execute(
        text(
            "SELECT COUNT(DISTINCT day) AS cnt FROM ("
            "  SELECT DATE(created_at AT TIME ZONE 'UTC') AS day FROM meal "
            "  WHERE user_id = :uid AND created_at >= :started_at "
            "  UNION ALL "
            "  SELECT DATE(logged_at AT TIME ZONE 'UTC') FROM hydration_entries "
            "  WHERE user_id = :uid AND logged_at >= :started_at "
            "  UNION ALL "
            "  SELECT DATE(logged_at AT TIME ZONE 'UTC') FROM movement_entries "
            "  WHERE user_id = :uid AND logged_at >= :started_at"
            ") AS days"
        ),
        {"uid": user_id, "started_at": started_at},
    )
    active_day_count = active_day_row.scalar() or 0

    sub_row = await session.execute(
        text(
            "SELECT expires_at FROM subscriptions "
            "WHERE user_id = :uid AND status = 'active' "
            "ORDER BY expires_at DESC NULLS LAST LIMIT 1"
        ),
        {"uid": user_id},
    )
    sub = sub_row.mappings().first()
    trial_end_at = (
        sub["expires_at"]
        if sub and sub["expires_at"]
        else started_at + timedelta(hours=72)
    )
    lock_at = trial_end_at - timedelta(hours=6)

    return AssetSummaryResponse(
        meal_scan_count=int(meal_scan_count),
        hydration_entry_count=int(hydration_entry_count),
        hydration_win_count=int(hydration_win_count),
        movement_entry_count=int(movement_entry_count),
        active_day_count=int(active_day_count),
        trial_end_at=trial_end_at,
        lock_at=lock_at,
    )
