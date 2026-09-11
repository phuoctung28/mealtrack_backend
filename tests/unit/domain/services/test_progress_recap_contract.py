from datetime import date

from src.domain.services.progress_recap_contract import (
    fallback_recap,
    parse_ai_recap,
)
from src.domain.services.progress_recap_facts import build_recap_facts


def _facts():
    return build_recap_facts(
        [
            {
                "date": "2026-09-07",
                "calories": 2100,
                "target_calories": 2000,
                "protein_g": 140,
                "protein_target_g": 130,
                "hydration_ml": 2000,
                "hydration_goal_ml": 2000,
                "burned_calories": 0,
                "meal_count": 3,
                "logged_status": "full",
            }
        ],
        horizon="week",
        start=date(2026, 9, 7),
        end=date(2026, 9, 13),
    )


def test_parse_ai_recap_keeps_horizon_kinds_only() -> None:
    payload = parse_ai_recap(
        {
            "headline": "Week stayed close.",
            "body": "Two logged days.",
            "next_move": "Keep protein first.",
            "highlights": [
                {
                    "kind": "pace",
                    "polarity": "watch",
                    "title": "Pace",
                    "detail": "+100 kcal",
                },
                {
                    "kind": "best_day",
                    "polarity": "win",
                    "title": "Best day",
                    "detail": "Sep 7",
                },
                {
                    "kind": "quality",
                    "polarity": "win",
                    "title": "Quality",
                    "detail": "not allowed for week",
                },
            ],
        },
        _facts(),
    )
    assert payload is not None
    kinds = [item["kind"] for item in payload["highlights"]]
    assert "quality" not in kinds
    assert kinds == ["pace", "best_day"]


def test_fallback_recap_uses_fact_numbers() -> None:
    payload = fallback_recap(_facts())
    assert payload["status"] == "ready"
    assert "100" in payload["headline"]
    assert len(payload["highlights"]) == 3


def test_fallback_recap_kinds_match_each_horizon() -> None:
    from src.domain.services.progress_recap_prompt import ALLOWED_KINDS

    days = [
        {
            "date": "2026-09-07",
            "calories": 2100,
            "target_calories": 2000,
            "protein_g": 140,
            "protein_target_g": 130,
            "hydration_ml": 2000,
            "hydration_goal_ml": 2000,
            "burned_calories": 0,
            "meal_count": 3,
            "logged_status": "full",
            "nrf_quality": 0.7,
            "nrf_coverage": 2,
        }
    ]
    seen: set[tuple[str, ...]] = set()
    for horizon, start, end in (
        ("day", date(2026, 9, 7), date(2026, 9, 7)),
        ("week", date(2026, 9, 7), date(2026, 9, 13)),
        ("month", date(2026, 9, 1), date(2026, 9, 30)),
        ("year", date(2026, 1, 1), date(2026, 12, 31)),
    ):
        facts = build_recap_facts(days, horizon=horizon, start=start, end=end)
        payload = fallback_recap(facts)
        kinds = tuple(item["kind"] for item in payload["highlights"])
        assert kinds
        assert all(kind in ALLOWED_KINDS[horizon] for kind in kinds)
        seen.add(kinds)
    assert len(seen) == 4
