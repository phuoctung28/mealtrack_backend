"""Backfill journey progress seeds from pre-release action logs.

Usage:
  python scripts/backfill_journey_progress_seed.py --dry-run
  python scripts/backfill_journey_progress_seed.py --cap-percent 70
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import select

from src.app.handlers.query_handlers.get_user_tdee_query_handler import (
    GetUserTdeeQueryHandler,
)
from src.app.queries.tdee import GetUserTdeeQuery
from src.domain.services.journey_progress_rules import (
    FEATURE_START_DATE,
    estimate_timeline_days,
)
from src.domain.services.journey_progress_service import calculate_journey_progress
from src.domain.utils.timezone_utils import ensure_utc, get_zone_info
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User
from src.infra.database.uow_async import AsyncUnitOfWork


def _feature_start_utc(timezone: str) -> datetime:
    user_tz = get_zone_info(timezone)
    return datetime.combine(FEATURE_START_DATE, time.min, tzinfo=user_tz).astimezone(
        UTC
    )


async def _load_targets(user_id: str) -> tuple[float, float]:
    result = await GetUserTdeeQueryHandler().handle(GetUserTdeeQuery(user_id=user_id))
    macros = result.get("macros") or {}
    return float(result.get("target_calories") or 0), float(macros.get("protein") or 0)


async def backfill(
    *,
    cap_percent: float,
    lookback_days: int,
    dry_run: bool,
    limit: int | None,
) -> int:
    updated = 0
    async with AsyncUnitOfWork() as uow:
        stmt = (
            select(UserProfile, User)
            .join(User, User.id == UserProfile.user_id)
            .where(
                User.is_active.is_(True),
                UserProfile.is_current.is_(True),
                UserProfile.journey_progress_seed_percent == 0,
            )
            .order_by(UserProfile.created_at.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        rows = (await uow.session.execute(stmt)).all()
        for profile, user in rows:
            user_tz = get_zone_info(user.timezone)
            feature_start = _feature_start_utc(user.timezone)
            raw_start = profile.goal_started_at or profile.created_at
            if raw_start is None:
                raw_start = feature_start - timedelta(days=lookback_days)

            history_start = max(
                ensure_utc(raw_start),
                feature_start - timedelta(days=lookback_days),
            )
            if history_start >= feature_start:
                continue

            start_weight = profile.goal_start_weight_kg or profile.weight_kg
            timeline_days = estimate_timeline_days(
                goal=profile.fitness_goal,
                start_weight_kg=start_weight,
                target_weight_kg=profile.target_weight_kg,
                challenge_duration=profile.challenge_duration,
            )
            actions = await _load_actions(
                uow, str(profile.user_id), history_start, feature_start
            )
            if not actions:
                continue

            target_calories, target_protein_g = await _load_targets(
                str(profile.user_id)
            )
            result = calculate_journey_progress(
                actions=actions,
                period_start=history_start,
                timeline_days=timeline_days,
                user_tz=user_tz,
                as_of=feature_start,
                target_calories=target_calories,
                target_protein_g=target_protein_g,
                water_goal_ml=profile.daily_water_goal_ml or 2000,
            )
            seed = min(cap_percent, result["progress_percent"])
            if seed <= 0:
                continue

            updated += 1
            print(f"{profile.user_id}: seed={seed:.3f}% actions={len(actions)}")
            if not dry_run:
                profile.journey_progress_seed_percent = seed

    return updated


async def _load_actions(uow, user_id: str, start_utc: datetime, end_utc: datetime):
    from src.app.handlers.query_handlers.get_journey_progress_query_handler import (
        GetJourneyProgressQueryHandler,
    )

    handler = GetJourneyProgressQueryHandler(uow=uow)
    return await handler._load_actions(uow, user_id, start_utc, end_utc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap-percent", type=float, default=70.0)
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.cap_percent < 0 or args.cap_percent > 100:
        raise SystemExit("--cap-percent must be between 0 and 100")
    if args.lookback_days <= 0:
        raise SystemExit("--lookback-days must be greater than 0")

    count = asyncio.run(
        backfill(
            cap_percent=args.cap_percent,
            lookback_days=args.lookback_days,
            dry_run=args.dry_run,
            limit=args.limit,
        )
    )
    action = "would update" if args.dry_run else "updated"
    print(f"{action} {count} profile(s)")


if __name__ == "__main__":
    main()
