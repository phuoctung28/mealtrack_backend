"""Capability discovery for durable writes."""

import pytest

from src.api.routes.v1.capabilities import get_durable_write_capabilities


@pytest.mark.asyncio
async def test_durable_write_capabilities_advertise_manual_meal_only():
    body = await get_durable_write_capabilities()
    assert body["retention_days"] == 14
    assert body["actions"]["manual_meal_create"]["supported"] is True
    assert body["actions"]["manual_meal_create"]["header"] == "Idempotency-Key"
    assert body["actions"]["weight_sync"]["supported"] is False
    assert body["actions"]["weight_sync"]["reason"] == "client_entry_id_mapping_pending"
