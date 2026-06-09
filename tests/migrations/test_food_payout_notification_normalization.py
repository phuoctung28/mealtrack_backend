from pathlib import Path

FOOD_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260609000005_normalize_food_notification_payout_details.py"
)
INDEX_MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260609000006_add_normalized_read_indexes.py"
)


def test_food_payout_migration_adds_normalized_tables_and_typed_fields() -> None:
    migration_text = FOOD_MIGRATION_PATH.read_text()

    assert '"food_reference_serving_sizes"' in migration_text
    assert '"food_reference_nutrients"' in migration_text
    assert '"payment_account_type"' in migration_text
    assert '"payment_account_masked"' in migration_text
    assert "payment_details" in migration_text
    assert "context_schema_version" in migration_text


def test_read_index_migration_targets_operational_paths() -> None:
    migration_text = INDEX_MIGRATION_PATH.read_text()

    assert "idx_user_fcm_tokens_user_active" in migration_text
    assert "idx_notifications_user_status_date" in migration_text
    assert "idx_notifications_processing_reclaim" in migration_text
