from datetime import datetime, timezone

from src.domain.model.hydration import HydrationEntry


def test_hydration_entry_derives_calories_from_macros() -> None:
    entry = HydrationEntry(
        user_id="user-1",
        drink_name_snapshot="Milk",
        volume_ml=250,
        credited_ml=200,
        protein_g=8,
        carbs_g=12,
        fat_g=5,
        fiber_g=1,
        logged_at=datetime(2026, 6, 9, tzinfo=timezone.utc),  # noqa: UP017
    )

    assert entry.calories == 123.0
