import importlib.util
from pathlib import Path

import pytest

MIGRATION = Path(
    "migrations/versions/20260730110500000000_restore_missing_meal_catalog_schema.py"
)


class _Inspector:
    def __init__(self, tables: dict[str, set[str]]) -> None:
        self.tables = tables

    def has_table(self, table_name: str) -> bool:
        return table_name in self.tables

    def get_columns(self, table_name: str) -> list[dict[str, str]]:
        return [{"name": name} for name in self.tables[table_name]]


class _Operations:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_bind(self) -> object:
        return object()

    def __getattr__(self, name: str):
        def operation(*_args, **_kwargs) -> None:
            self.calls.append(name)

        return operation


def _load_migration():
    spec = importlib.util.spec_from_file_location("catalog_schema_repair", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repair_creates_missing_catalog_branch_from_an_empty_catalog_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration()
    operations = _Operations()
    baseline_calls: list[bool] = []

    monkeypatch.setattr(module, "op", operations)
    monkeypatch.setattr(
        module.sa,
        "inspect",
        lambda _bind: _Inspector({"food_reference": {"id", "name_normalized"}}),
    )
    monkeypatch.setattr(
        module,
        "_run_catalog_baseline_upgrade",
        lambda: baseline_calls.append(True),
    )

    module.upgrade()

    assert baseline_calls == [True]
    assert operations.calls.count("add_column") == 4
    assert operations.calls.count("create_check_constraint") == 3
    assert operations.calls.count("drop_constraint") == 2
    assert operations.calls.count("execute") == 3


def test_repair_leaves_complete_catalog_schema_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration()
    operations = _Operations()
    catalog_tables = {name: {"id"} for name in module.CATALOG_TABLES}
    catalog_tables["food_reference"] = {"id", "name_normalized"}

    monkeypatch.setattr(module, "op", operations)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: _Inspector(catalog_tables))
    monkeypatch.setattr(
        module,
        "_run_catalog_baseline_upgrade",
        lambda: pytest.fail("baseline must not run for a complete catalog schema"),
    )

    module.upgrade()

    assert operations.calls == ["execute", "execute"]


def test_repair_fails_closed_for_a_partial_catalog_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_migration()
    operations = _Operations()

    monkeypatch.setattr(module, "op", operations)
    monkeypatch.setattr(
        module.sa,
        "inspect",
        lambda _bind: _Inspector(
            {
                "food_reference": {"id", "name_normalized"},
                "meal_catalog": {"id"},
            }
        ),
    )

    with pytest.raises(RuntimeError, match="Catalog schema is partially present"):
        module.upgrade()

    assert operations.calls == []
