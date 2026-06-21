"""Period and timeline rules for journey progress."""

from datetime import UTC, date, datetime, time
from math import ceil
from zoneinfo import ZoneInfo

from src.domain.utils.timezone_utils import ensure_utc

FEATURE_START_DATE = date(2026, 6, 21)
RECOMP_TIMELINE_DAYS = 84
MINIMUM_TIMELINE_DAYS = 7
MAXIMUM_TIMELINE_DAYS = 730
CUT_PACE_KG_PER_WEEK = 0.5
BULK_PACE_KG_PER_WEEK = 0.25


def journey_period_start(
    *,
    goal_started_at: datetime | None,
    user_tz: ZoneInfo,
) -> datetime:
    local_start = datetime.combine(FEATURE_START_DATE, time.min, tzinfo=user_tz)
    feature_start = local_start.astimezone(UTC)
    if goal_started_at is not None:
        return max(ensure_utc(goal_started_at), feature_start)

    return feature_start


def estimate_timeline_days(
    *,
    goal: str | None,
    start_weight_kg: float | None,
    target_weight_kg: float | None,
    challenge_duration: str | None = None,
) -> int:
    challenge_days = _challenge_days(challenge_duration)
    if challenge_days is not None:
        return challenge_days
    if goal == "recomp":
        return RECOMP_TIMELINE_DAYS
    if start_weight_kg is None or target_weight_kg is None:
        return RECOMP_TIMELINE_DAYS

    delta_kg = abs(start_weight_kg - target_weight_kg)
    if delta_kg < 0.1:
        return MINIMUM_TIMELINE_DAYS

    pace = BULK_PACE_KG_PER_WEEK if goal == "bulk" else CUT_PACE_KG_PER_WEEK
    days = ceil((delta_kg / pace) * 7)
    return max(MINIMUM_TIMELINE_DAYS, min(MAXIMUM_TIMELINE_DAYS, days))


def _challenge_days(value: str | None) -> int | None:
    if not value or not value.endswith("_days"):
        return None
    try:
        days = int(value.removesuffix("_days"))
    except ValueError:
        return None
    return max(MINIMUM_TIMELINE_DAYS, min(MAXIMUM_TIMELINE_DAYS, days))
