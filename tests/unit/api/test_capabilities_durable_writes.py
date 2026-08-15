"""Capability discovery for durable writes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.api.routes.v1.capabilities import durable_write_capabilities


@pytest.mark.asyncio
async def test_durable_write_capabilities_advertise_legacy_and_v2_contracts():
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
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(all=lambda: rows)
    uow = AsyncMock()
    uow.__aenter__.return_value = SimpleNamespace(session=session)
    with patch(
        "src.api.routes.v1.capabilities.AsyncUnitOfWork", return_value=uow
    ):
        body = await durable_write_capabilities()

    assert body["retention_days"] == 14
    assert body["actions"]["manual_meal_create"]["supported"] is True
    assert body["actions"]["manual_meal_create"]["header"] == "Idempotency-Key"
    assert body["actions"]["weight_sync"]["supported"] is False
    assert body["actions"]["weight_sync"]["reason"] == "client_entry_id_mapping_pending"
    assert body["durable_writes"] is True
    assert body["nutrition_contract_version"] == 2
    assert body["operations"] == ["create_manual_meal", "edit_meal"]
