from datetime import date
from types import SimpleNamespace

from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)


def test_notification_row_builder_sets_context_schema_version() -> None:
    service = DailyContextPrecomputeService()
    rows = service._build_notification_rows(
        pref_rows=[
            SimpleNamespace(
                user_id="user-1",
                language="en",
                meal_reminders_enabled=True,
                breakfast_time_minutes=480,
                lunch_time_minutes=None,
                dinner_time_minutes=None,
                daily_summary_enabled=True,
                daily_summary_time_minutes=None,
                hydration_reminders_enabled=True,
            )
        ],
        tokens_by_user={"user-1": ["token-1"]},
        calorie_goals={"user-1": 2000},
        consumed_by_user={"user-1": 300},
        profiles_by_user={"user-1": SimpleNamespace(gender="male", language_code="en")},
        today=date(2026, 6, 9),
        tz_name="UTC",
    )

    assert rows
    assert {row["context_schema_version"] for row in rows} == {1}
