"""Horizon-specific recap copy when AI is unavailable."""

from __future__ import annotations

from src.domain.services.progress_recap_facts import RecapFacts
from src.domain.services.progress_recap_prompt import ALLOWED_KINDS


def fallback_copy(facts: RecapFacts) -> tuple[str, str, str, list[dict[str, str]]]:
    headline, body, next_move, highlights = {
        "day": _day,
        "week": _week,
        "month": _month,
        "year": _year,
    }[facts.horizon](facts)
    allowed = ALLOWED_KINDS[facts.horizon]
    return headline, body, next_move, [item for item in highlights if item["kind"] in allowed][:3]


def _day(facts: RecapFacts) -> tuple[str, str, str, list[dict[str, str]]]:
    over = facts.balance_kcal > 0
    headline = (
        f"{abs(facts.balance_kcal):.0f} kcal over today's target."
        if over
        else f"{abs(facts.balance_kcal):.0f} kcal left today."
    )
    body = (
        f"Protein {facts.protein_avg:.0f} g of {facts.protein_target_avg:.0f} g. "
        f"Water {facts.hydration_avg:.0f} ml of {facts.hydration_goal_avg:.0f} ml."
    )
    protein_ok = (
        facts.protein_target_avg > 0
        and facts.protein_avg >= 0.9 * facts.protein_target_avg
    )
    hydro_ok = (
        facts.hydration_goal_avg > 0
        and facts.hydration_avg >= 0.9 * facts.hydration_goal_avg
    )
    next_move = _next_move(facts)
    return headline, body, next_move, [
        _beat(
            "protein",
            "win" if protein_ok else "watch",
            "Protein",
            f"{facts.protein_avg:.0f} g vs {facts.protein_target_avg:.0f} g target.",
        ),
        _beat(
            "hydration",
            "win" if hydro_ok else "watch",
            "Water",
            f"{facts.hydration_avg:.0f} ml vs {facts.hydration_goal_avg:.0f} ml goal.",
        ),
        _beat("next_move", "next", "Tonight", next_move),
    ]


def _week(facts: RecapFacts) -> tuple[str, str, str, list[dict[str, str]]]:
    next_move = _next_move(facts)
    watch = (
        _beat(
            "swing",
            "watch",
            "Swing",
            f"Daily calories swung {facts.swing_cv:.0%} around the average.",
        )
        if facts.swing_cv is not None and facts.swing_cv >= 0.18
        else _beat(
            "protein_hits",
            "watch" if facts.protein_hit_days < facts.logged_days else "win",
            "Protein days",
            f"Hit protein on {facts.protein_hit_days} of {facts.logged_days} logged days.",
        )
    )
    win = (
        _beat(
            "best_day",
            "win",
            "Closest day",
            f"{facts.best_day} landed {abs(facts.best_day_balance_kcal or 0):.0f} kcal from target.",
        )
        if facts.best_day
        else _beat(
            "consistency",
            "win",
            "Logging",
            f"{facts.logged_days} of {facts.total_days} days have meals.",
        )
    )
    return _balance_headline(facts), _logged_body(facts), next_move, [
        win,
        watch,
        _beat("next_move", "next", "This week", next_move),
    ]


def _month(facts: RecapFacts) -> tuple[str, str, str, list[dict[str, str]]]:
    next_move = _next_move(facts)
    gap = facts.weekend_gap_kcal
    headline = (
        f"Weekends run {abs(gap):.0f} kcal {'above' if gap > 0 else 'below'} weekdays."
        if gap is not None and abs(gap) >= 150
        else _balance_headline(facts)
    )
    win = (
        _beat("best_week", "win", "Steadiest week", f"{facts.best_week} stayed closest to target.")
        if facts.best_week
        else _beat(
            "consistency",
            "win",
            "Logging",
            f"{facts.logged_days} of {facts.total_days} days have meals.",
        )
    )
    watch = (
        _beat(
            "weekend_gap",
            "watch",
            "Weekend gap",
            f"Weekends average {gap:+.0f} kcal versus weekdays.",
        )
        if gap is not None
        else _beat(
            "protein_hits",
            "watch",
            "Protein days",
            f"Hit protein on {facts.protein_hit_days} of {facts.logged_days} logged days.",
        )
    )
    return headline, _logged_body(facts), next_move, [
        win,
        watch,
        _beat("next_move", "next", "This month", next_move),
    ]


def _year(facts: RecapFacts) -> tuple[str, str, str, list[dict[str, str]]]:
    next_move = _next_move(facts)
    headline = f"Logged {facts.logged_days} of {facts.total_days} days this year."
    win = (
        _beat("best_month", "win", "Steadiest month", f"{facts.best_month} stayed closest to target.")
        if facts.best_month
        else _beat(
            "consistency",
            "win",
            "Logging",
            f"{facts.logged_days} of {facts.total_days} days have meals.",
        )
    )
    watch = (
        _beat(
            "quality",
            "watch" if facts.quality_avg < 0.6 else "win",
            "Food quality",
            f"Average quality score is {facts.quality_avg:.2f} across covered days.",
        )
        if facts.quality_avg is not None
        else _beat(
            "pace",
            "watch" if facts.balance_kcal > 0 else "win",
            "Year pace",
            f"Window balance is {facts.balance_kcal:+.0f} kcal versus target.",
        )
    )
    return headline, _logged_body(facts), next_move, [
        win,
        watch,
        _beat("next_move", "next", "This year", next_move),
    ]


def _balance_headline(facts: RecapFacts) -> str:
    side = "over" if facts.balance_kcal > 0 else "under"
    return f"{abs(facts.balance_kcal):.0f} kcal {side} the {facts.horizon} target."


def _logged_body(facts: RecapFacts) -> str:
    return f"{facts.logged_days} of {facts.total_days} days logged. Protein hit {facts.protein_hit_days} days."


def _next_move(facts: RecapFacts) -> str:
    if (
        facts.protein_target_avg > 0
        and facts.protein_avg < 0.9 * facts.protein_target_avg
    ):
        gap = facts.protein_target_avg - facts.protein_avg
        return f"Add about {gap:.0f} g protein in the next meal."
    if facts.balance_kcal > 80:
        return "Keep the next meal protein-forward and simple."
    if facts.horizon == "day":
        return "Repeat this meal rhythm tonight."
    return "Repeat yesterday's rhythm — it is working."


def _beat(kind: str, polarity: str, title: str, detail: str) -> dict[str, str]:
    return {"kind": kind, "polarity": polarity, "title": title, "detail": detail}
