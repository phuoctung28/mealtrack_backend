"""Paddle server environment and webhook persistence tests."""

import pytest
from sqlalchemy.dialects import postgresql

from src.infra.services.paddle_client import is_paddle_sandbox
from src.infra.services.paddle_fulfillment_service import _handle_subscription


def test_sandbox_environment_is_marked_as_sandbox(monkeypatch):
    monkeypatch.setenv("PADDLE_ENVIRONMENT", "sandbox")

    assert is_paddle_sandbox() is True


def test_live_environment_is_not_marked_as_sandbox(monkeypatch):
    monkeypatch.setenv("PADDLE_ENVIRONMENT", "production")

    assert is_paddle_sandbox() is False


class _UnlinkedUserResult:
    def scalar_one_or_none(self):
        return None


class _CapturingSession:
    def __init__(self):
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        if len(self.statements) == 1:
            return _UnlinkedUserResult()
        return None


@pytest.mark.asyncio
async def test_subscription_upsert_persists_sandbox_flag_on_conflict(monkeypatch):
    monkeypatch.setenv("PADDLE_ENVIRONMENT", "sandbox")
    session = _CapturingSession()

    await _handle_subscription(
        session,
        {
            "id": "sub_test",
            "customer_id": "ctm_test",
            "status": "active",
            "created_at": "2026-07-31T00:00:00Z",
            "updated_at": "2026-07-31T00:00:00Z",
            "items": [{"price": {"id": "pri_test", "product_id": "pro_test"}}],
        },
    )

    statement = session.statements[-1]
    compiled = statement.compile(dialect=postgresql.dialect())

    assert compiled.params["is_sandbox"] is True
    assert "is_sandbox = excluded.is_sandbox" in str(compiled)
