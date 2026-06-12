from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260609000002_normalize_user_profile_preferences.py"
)


def test_profile_preference_migration_backfills_all_legacy_arrays() -> None:
    migration_text = MIGRATION_PATH.read_text()

    for field_name in (
        "dietary_preferences",
        "health_conditions",
        "allergies",
        "pain_points",
        "referral_sources",
        "training_types",
    ):
        assert field_name in migration_text

    assert "jsonb_typeof(source.raw_values::jsonb) = 'array'" in migration_text
    assert (
        "DISTINCT ON (profile_id, preference_type, normalized_value)" in migration_text
    )
    assert (
        "ON CONFLICT (profile_id, preference_type, value) DO NOTHING" in migration_text
    )
