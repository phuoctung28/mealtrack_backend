"""Journey progress period and scoring helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.domain.utils.timezone_utils import ensure_utc

COMPLETE_MEAL_COUNT = 3
MINIMUM_LOGGED_ACTION_PERCENT = 0.1
EMPTY_BREAKDOWN = {
    "calories_points": 0.0,
    "logging_points": 0.0,
    "protein_points": 0.0,
    "hydration_points": 0.0,
    "activity_points": 0.0,
}


@dataclass(frozen=True)
class JourneyAction:
    source: str
    label: str
    logged_at: datetime
    calories: float = 0.0
    protein_g: float = 0.0
    hydration_ml: int = 0


@dataclass
class DayTotals:
    calories: float = 0.0
    protein_g: float = 0.0
    meal_count: int = 0
    hydration_ml: int = 0
    movement_count: int = 0
    action_count: int = 0


def calculate_journey_progress(
    *,
    actions: list[JourneyAction],
    period_start: datetime,
    timeline_days: int,
    user_tz: ZoneInfo,
    as_of: datetime,
    target_calories: float,
    target_protein_g: float,
    water_goal_ml: int,
) -> dict:
    period_end = period_start + timedelta(days=timeline_days)
    effective_end = min(as_of, period_end)
    included = [
        action
        for action in actions
        if period_start <= ensure_utc(action.logged_at) < effective_end
    ]
    daily_budget = 100 / timeline_days
    buckets = _bucket_actions(included, user_tz)
    as_of_local_date = as_of.astimezone(user_tz).date()

    confirmed = 0.0
    provisional = 0.0
    breakdown = EMPTY_BREAKDOWN.copy()
    for day, totals in buckets.items():
        points = _score_day(
            totals,
            target_calories=target_calories,
            target_protein_g=target_protein_g,
            water_goal_ml=water_goal_ml,
        )
        percent = _day_percent(points, totals.action_count, daily_budget)
        if day == as_of_local_date and as_of < period_end:
            provisional += percent
            breakdown = points
        else:
            confirmed += percent

    display = min(100.0, confirmed + provisional)
    latest = max(
        included, key=lambda action: ensure_utc(action.logged_at), default=None
    )
    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "as_of": as_of.isoformat(),
        "progress_percent": round(display, 3),
        "confirmed_progress_percent": round(min(100.0, confirmed), 3),
        "provisional_progress_percent": round(
            min(100.0, max(0.0, display - confirmed)), 3
        ),
        "timeline_days": timeline_days,
        "daily_progress_budget_percent": round(daily_budget, 3),
        "score": round(sum(breakdown.values())),
        "breakdown": {key: round(value, 3) for key, value in breakdown.items()},
        "latest_action": _action_dict(latest),
        "is_week_over_budget": False,
    }


def _bucket_actions(
    actions: list[JourneyAction], user_tz: ZoneInfo
) -> dict[date, DayTotals]:
    buckets: dict[date, DayTotals] = {}
    for action in actions:
        day = ensure_utc(action.logged_at).astimezone(user_tz).date()
        totals = buckets.setdefault(day, DayTotals())
        totals.action_count += 1
        if action.source == "meal":
            totals.meal_count += 1
        elif action.source == "hydration":
            totals.hydration_ml += action.hydration_ml
        elif action.source == "activity":
            totals.movement_count += 1
        totals.calories += action.calories
        totals.protein_g += action.protein_g
    return buckets


def _score_day(
    totals: DayTotals,
    *,
    target_calories: float,
    target_protein_g: float,
    water_goal_ml: int,
) -> dict[str, float]:
    return {
        "calories_points": _calorie_adherence(target_calories, totals.calories) * 30,
        "logging_points": min(1.0, totals.meal_count / COMPLETE_MEAL_COUNT) * 20,
        "protein_points": _target_progress(target_protein_g, totals.protein_g) * 15,
        "hydration_points": _target_progress(water_goal_ml, totals.hydration_ml) * 15,
        "activity_points": min(1.0, totals.movement_count) * 20,
    }


def _day_percent(
    points: dict[str, float], action_count: int, daily_budget: float
) -> float:
    if action_count <= 0:
        return 0.0
    scored = daily_budget * (sum(points.values()) / 100)
    floor = min(daily_budget, action_count * MINIMUM_LOGGED_ACTION_PERCENT)
    return min(daily_budget, max(floor, scored))


def _calorie_adherence(target: float, consumed: float) -> float:
    if target <= 0 or consumed <= 0:
        return 0.0
    return max(0.0, min(1.0, 1 - abs(1 - consumed / target)))


def _target_progress(target: float, consumed: float) -> float:
    if target <= 0 or consumed <= 0:
        return 0.0
    return max(0.0, min(1.0, consumed / target))


def _action_dict(action: JourneyAction | None) -> dict | None:
    if action is None:
        return None
    return {
        "source": action.source,
        "label": action.label,
        "logged_at": ensure_utc(action.logged_at).isoformat(),
    }
