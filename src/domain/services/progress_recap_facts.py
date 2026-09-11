"""Deterministic recap facts from a progress-summary window."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from statistics import mean
from typing import Any

HORIZONS = frozenset({"day", "week", "month", "year"})


@dataclass(frozen=True)
class RecapFacts:
    horizon: str
    start: str
    end: str
    total_days: int
    logged_days: int
    calories_sum: float
    target_sum: float
    balance_kcal: float
    calorie_avg: float
    target_avg: float
    protein_avg: float
    protein_target_avg: float
    protein_hit_days: int
    hydration_avg: float
    hydration_goal_avg: float
    hydration_hit_days: int
    burn_total: float
    quality_avg: float | None
    best_day: str | None
    best_day_balance_kcal: float | None
    swing_cv: float | None
    weekend_gap_kcal: float | None
    best_week: str | None
    best_month: str | None

    def to_prompt_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_recap_facts(
    days: list[dict[str, Any]],
    *,
    horizon: str,
    start: date,
    end: date,
) -> RecapFacts:
    logged = [row for row in days if _is_logged(row)]
    calories = [_num(row, "calories") for row in logged]
    targets = [_num(row, "target_calories") for row in logged]
    proteins = [_num(row, "protein_g") for row in logged]
    protein_targets = [_num(row, "protein_target_g") for row in logged]
    hydrations = [_num(row, "hydration_ml") for row in logged]
    hydration_goals = [_num(row, "hydration_goal_ml") for row in logged]
    quality_vals = [
        _num(row, "nrf_quality")
        for row in logged
        if int(row.get("nrf_coverage") or 0) > 0
    ]
    cal_sum = sum(calories)
    tgt_sum = sum(targets)
    best = _best_day(logged)
    return RecapFacts(
        horizon=horizon,
        start=start.isoformat(),
        end=end.isoformat(),
        total_days=max((end - start).days + 1, 0),
        logged_days=len(logged),
        calories_sum=round(cal_sum, 1),
        target_sum=round(tgt_sum, 1),
        balance_kcal=round(cal_sum - tgt_sum, 1),
        calorie_avg=round(mean(calories), 1) if calories else 0.0,
        target_avg=round(mean(targets), 1) if targets else 0.0,
        protein_avg=round(mean(proteins), 1) if proteins else 0.0,
        protein_target_avg=round(mean(protein_targets), 1) if protein_targets else 0.0,
        protein_hit_days=sum(
            1
            for row in logged
            if _num(row, "protein_target_g") > 0
            and _num(row, "protein_g") >= 0.9 * _num(row, "protein_target_g")
        ),
        hydration_avg=round(mean(hydrations), 1) if hydrations else 0.0,
        hydration_goal_avg=round(mean(hydration_goals), 1) if hydration_goals else 0.0,
        hydration_hit_days=sum(
            1
            for row in logged
            if _num(row, "hydration_goal_ml") > 0
            and _num(row, "hydration_ml") >= 0.9 * _num(row, "hydration_goal_ml")
        ),
        burn_total=round(sum(_num(row, "burned_calories") for row in logged), 1),
        quality_avg=round(mean(quality_vals), 2) if quality_vals else None,
        best_day=best[0],
        best_day_balance_kcal=best[1],
        swing_cv=_calorie_cv(calories),
        weekend_gap_kcal=_weekend_gap(logged),
        best_week=_best_bucket(logged, _iso_week),
        best_month=_best_bucket(logged, _year_month),
    )


def _is_logged(row: dict[str, Any]) -> bool:
    if int(row.get("meal_count") or 0) > 0:
        return True
    return str(row.get("logged_status") or "none") != "none"


def _num(row: dict[str, Any], key: str) -> float:
    try:
        return float(row.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def _best_day(logged: list[dict[str, Any]]) -> tuple[str | None, float | None]:
    best_key: str | None = None
    best_abs = float("inf")
    best_balance: float | None = None
    for row in logged:
        target = _num(row, "target_calories")
        if target <= 0:
            continue
        balance = _num(row, "calories") - target
        if abs(balance) < best_abs:
            best_abs = abs(balance)
            best_key = str(row.get("date") or "") or None
            best_balance = round(balance, 1)
    return best_key, best_balance


def _calorie_cv(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    avg = mean(values)
    if avg <= 0:
        return None
    variance = mean(abs(value - avg) for value in values)
    return round(variance / avg, 3)


def _weekend_gap(logged: list[dict[str, Any]]) -> float | None:
    weekday: list[float] = []
    weekend: list[float] = []
    for row in logged:
        day = _parse_date(row.get("date"))
        if day is None:
            continue
        bucket = weekend if day.weekday() >= 5 else weekday
        bucket.append(_num(row, "calories"))
    if not weekday or not weekend:
        return None
    return round(mean(weekend) - mean(weekday), 1)


def _best_bucket(logged: list[dict[str, Any]], key_fn: Any) -> str | None:
    buckets: dict[str, list[float]] = defaultdict(list)
    for row in logged:
        day = _parse_date(row.get("date"))
        target = _num(row, "target_calories")
        if day is None or target <= 0:
            continue
        buckets[key_fn(day)].append(abs(_num(row, "calories") / target - 1))
    if not buckets:
        return None
    return min(buckets, key=lambda key: mean(buckets[key]))


def _iso_week(value: date) -> str:
    iso = value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _year_month(value: date) -> str:
    return f"{value.year}-{value.month:02d}"


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
