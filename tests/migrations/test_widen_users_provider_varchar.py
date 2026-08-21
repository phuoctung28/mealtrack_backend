import importlib.util
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

MIGRATION = Path("migrations/versions/20260818000002_widen_users_provider_varchar.py")


class _Inspector:
    def __init__(
        self,
        *,
        has_users: bool = True,
        provider_type: object | None = None,
    ) -> None:
        self._has_users = has_users
        self._provider_type = provider_type

    def has_table(self, table_name: str) -> bool:
        return self._has_users and table_name == "users"

    def get_columns(self, table_name: str) -> list[dict[str, object]]:
        if table_name != "users" or self._provider_type is None:
            return []
        return [{"name": "provider", "type": self._provider_type}]


class _Operations:
    def __init__(self) -> None:
        self.execute_sql: list[str] = []

    def get_bind(self) -> object:
        return object()

    def execute(self, clause) -> None:
        self.execute_sql.append(str(clause))


def _load_migration():
    spec = importlib.util.spec_from_file_location("widen_users_provider", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_widen_provider_migration_is_idempotent_and_cast_through_text() -> None:
    text = MIGRATION.read_text()

    assert 'revision = "20260818000002"' in text
    assert 'down_revision = "20260818000001"' in text
    assert "VARCHAR(32)" in text
    assert "USING provider::text" in text
    assert "EMAIL_LINK" in text


def test_upgrade_widens_short_varchar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration()
    operations = _Operations()
    monkeypatch.setattr(module, "op", operations)
    monkeypatch.setattr(
        module.sa,
        "inspect",
        lambda _bind: _Inspector(provider_type=module.sa.String(6)),
    )

    module.upgrade()

    assert operations.execute_sql
    assert "VARCHAR(32)" in operations.execute_sql[0]


def test_upgrade_skips_when_already_wide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration()
    operations = _Operations()
    monkeypatch.setattr(module, "op", operations)
    monkeypatch.setattr(
        module.sa,
        "inspect",
        lambda _bind: _Inspector(provider_type=module.sa.String(32)),
    )

    module.upgrade()

    assert operations.execute_sql == []


def test_alembic_head_is_widen_provider_revision() -> None:
    script_dir = ScriptDirectory.from_config(Config("alembic.ini"))

    assert script_dir.get_heads() == ["20260818000002"]
    assert script_dir.get_current_head() == "20260818000002"
