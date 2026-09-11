from datetime import date

from src.domain.services.progress_recap_facts import build_recap_facts


def _day(date_key: str, calories: float, target: float, protein: float = 120) -> dict:
    return {
        "date": date_key,
        "calories": calories,
        "target_calories": target,
        "protein_g": protein,
        "protein_target_g": 130,
        "hydration_ml": 1800,
        "hydration_goal_ml": 2000,
        "burned_calories": 200,
        "meal_count": 3,
        "logged_status": "full",
        "nrf_quality": 0.7,
        "nrf_coverage": 2,
    }


def test_week_facts_count_logged_days_and_balance() -> None:
    facts = build_recap_facts(
        [
            _day("2026-09-07", 2200, 2000),
            _day("2026-09-08", 1900, 2000, protein=80),
            {"date": "2026-09-09", "meal_count": 0, "logged_status": "none"},
        ],
        horizon="week",
        start=date(2026, 9, 7),
        end=date(2026, 9, 13),
    )
    assert facts.logged_days == 2
    assert facts.total_days == 7
    assert facts.balance_kcal == 100.0
    assert facts.protein_hit_days == 1
    assert facts.best_day == "2026-09-08"


def test_month_facts_include_weekend_gap() -> None:
    days = [
        _day("2026-09-07", 1800, 2000),  # Monday
        _day("2026-09-08", 1800, 2000),
        _day("2026-09-12", 2400, 2000),  # Saturday
        _day("2026-09-13", 2400, 2000),  # Sunday
    ]
    facts = build_recap_facts(
        days,
        horizon="month",
        start=date(2026, 9, 1),
        end=date(2026, 9, 13),
    )
    assert facts.weekend_gap_kcal == 600.0
    assert facts.best_week is not None
