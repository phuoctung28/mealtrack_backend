import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "import_food_seeds.py"
_SPEC = importlib.util.spec_from_file_location("import_food_seeds", _SCRIPT_PATH)
assert _SPEC is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)


@pytest.mark.asyncio
async def test_import_uses_verified_normalized_seed_for_nin_food(tmp_path, monkeypatch):
    _write_entries(tmp_path, [_nin_entry()])
    repository = _Repository(existing=None)
    monkeypatch.setattr(_MODULE, "AsyncUnitOfWork", lambda: _UnitOfWork(repository))

    await _MODULE._run_import(tmp_path, dry_run=False, source_filter=None)

    prepared = repository.upsert_seed.await_args.args[0]
    assert prepared["name_normalized"] == "chicken breast"
    assert prepared["is_verified"] is True
    repository.upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_keeps_existing_higher_priority_source(tmp_path, monkeypatch):
    _write_entries(tmp_path, [_nin_entry(source="openfoodfacts")])
    repository = _Repository(existing={"source": "nin_vn", "is_verified": True})
    monkeypatch.setattr(_MODULE, "AsyncUnitOfWork", lambda: _UnitOfWork(repository))

    await _MODULE._run_import(tmp_path, dry_run=False, source_filter=None)

    repository.upsert_seed.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_keeps_existing_manually_verified_reference(tmp_path, monkeypatch):
    _write_entries(tmp_path, [_nin_entry()])
    repository = _Repository(existing={"source": "catalog_seed", "is_verified": True})
    monkeypatch.setattr(_MODULE, "AsyncUnitOfWork", lambda: _UnitOfWork(repository))

    await _MODULE._run_import(tmp_path, dry_run=False, source_filter=None)

    repository.upsert_seed.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_preserves_barcode_product_path(tmp_path, monkeypatch):
    entry = _nin_entry(source="openfoodfacts")
    entry["barcode"] = "8938505974199"
    _write_entries(tmp_path, [entry])
    repository = _Repository(existing=None)
    monkeypatch.setattr(_MODULE, "AsyncUnitOfWork", lambda: _UnitOfWork(repository))

    await _MODULE._run_import(tmp_path, dry_run=False, source_filter=None)

    repository.get_by_barcode.assert_awaited_once_with("8938505974199")
    repository.upsert.assert_awaited_once()
    assert repository.upsert.await_args.args[0]["is_verified"] is False
    repository.upsert_seed.assert_not_awaited()


@pytest.mark.asyncio
async def test_dry_run_does_not_open_database_transaction(tmp_path, monkeypatch):
    _write_entries(tmp_path, [_nin_entry()])
    open_uow = AsyncMock()
    monkeypatch.setattr(_MODULE, "AsyncUnitOfWork", open_uow)

    await _MODULE._run_import(tmp_path, dry_run=True, source_filter=None)

    open_uow.assert_not_called()


def test_fetch_nin_dishes_uses_dishes_only_scraper(tmp_path, monkeypatch):
    commands = []

    def fake_run(command, text):
        commands.append(command)
        (tmp_path / "nin_vn_dishes.json").write_text("[]", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(_MODULE.subprocess, "run", fake_run)

    assert _MODULE._fetch_nin_dishes(tmp_path) is True
    assert commands[0][2:] == [
        "--dishes-only",
        "--output-dishes",
        str(tmp_path / "nin_vn_dishes.json"),
    ]


class _Repository:
    def __init__(self, *, existing):
        self.existing = existing
        self.find_by_normalized_name = AsyncMock(return_value=existing)
        self.get_by_barcode = AsyncMock(return_value=None)
        self.upsert_seed = AsyncMock()
        self.upsert = AsyncMock()


class _UnitOfWork:
    def __init__(self, repository):
        self.food_references = repository

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None


def _nin_entry(*, source="nin_vn"):
    return {
        "name": "Chicken breast",
        "name_vi": "Ức gà",
        "category": "Poultry",
        "region": "VN",
        "source": source,
        "protein_100g": 31.0,
        "carbs_100g": 0.0,
        "fat_100g": 3.6,
    }


def _write_entries(directory, entries):
    (directory / "seeds.json").write_text(json.dumps(entries), encoding="utf-8")
