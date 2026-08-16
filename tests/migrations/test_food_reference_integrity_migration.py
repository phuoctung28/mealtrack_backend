from pathlib import Path

MIGRATION = next(
    Path("migrations/versions").glob("*_add_food_reference_integrity_state.py")
)


def test_integrity_migration_is_additive_and_append_only():
    text = MIGRATION.read_text()

    for column in (
        "integrity_status",
        "integrity_policy_version",
        "integrity_checked_at",
        "integrity_reason",
        "integrity_input_digest",
        "integrity_review_reference",
    ):
        assert f'"{column}"' in text
    assert "food_reference_integrity_control" in text
    assert "food_reference_integrity_event" in text
    assert "BEFORE UPDATE OR DELETE" in text
    assert "active_policy_version" in text
    assert "catalog_integrity_generation" in text
    assert "lock_timeout" in text
    assert "statement_timeout" in text
    assert "NOT VALID" in text


def test_integrity_migration_downgrade_refuses_to_delete_a_non_empty_ledger():
    text = MIGRATION.read_text()

    assert "preserve the append-only ledger" in text
    assert "ledger_count" in text
    assert "raise RuntimeError" in text
