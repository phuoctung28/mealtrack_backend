from src.infra.services.durable_write_service import _durable_write_schema_is_ready


def test_durable_write_capability_requires_all_storage_columns():
    rows = [
        (table, column)
        for table, columns in {
            "food_item": {
                "source_kind",
                "source_food_id",
                "nutrition_contract_version",
                "source_snapshot",
            },
            "meal_write_operation": {
                "user_id",
                "operation",
                "idempotency_key",
                "request_fingerprint",
                "status",
                "lease_owner",
                "lease_generation",
                "lease_expires_at",
                "target_meal_id",
                "response",
            },
        }.items()
        for column in columns
    ]

    assert _durable_write_schema_is_ready(rows)


def test_durable_write_capability_rejects_partial_snapshot_schema():
    assert not _durable_write_schema_is_ready([("meal_write_operation", "user_id")])
