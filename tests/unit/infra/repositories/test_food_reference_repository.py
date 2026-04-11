"""Unit tests for FoodReferenceRepository with mocked SQLAlchemy session."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.infra.repositories.food_reference_repository import FoodReferenceRepository


def _fake_row(**overrides):
    base = dict(
        id=1,
        barcode="123",
        name="Apple",
        name_vi=None,
        brand=None,
        category="fruit",
        region="global",
        fdc_id=99,
        protein_100g=0.1,
        carbs_100g=14.0,
        fat_100g=0.2,
        fiber_100g=2.0,
        sugar_100g=10.0,
        serving_sizes=None,
        density=1.0,
        serving_size="100g",
        extra_nutrients=None,
        source="test",
        is_verified=False,
        image_url=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def patched_session():
    session = MagicMock()
    with patch(
        "src.infra.repositories.food_reference_repository.SessionLocal",
        return_value=session,
    ):
        yield session


def test_get_by_barcode_returns_mapped_dict(patched_session):
    patched_session.execute.return_value.scalar_one_or_none.return_value = _fake_row()
    repo = FoodReferenceRepository()
    out = repo.get_by_barcode("123")
    assert out["barcode"] == "123"
    assert out["name"] == "Apple"
    patched_session.close.assert_called_once()


def test_get_by_barcode_returns_none_when_missing(patched_session):
    patched_session.execute.return_value.scalar_one_or_none.return_value = None
    repo = FoodReferenceRepository()
    assert repo.get_by_barcode("missing") is None


def test_get_by_barcode_returns_none_on_exception(patched_session):
    patched_session.execute.side_effect = RuntimeError("db down")
    repo = FoodReferenceRepository()
    assert repo.get_by_barcode("x") is None
    patched_session.close.assert_called_once()


def test_get_by_id_and_get_by_fdc_id(patched_session):
    patched_session.execute.return_value.scalar_one_or_none.return_value = _fake_row(
        id=5, fdc_id=555
    )
    repo = FoodReferenceRepository()
    assert repo.get_by_id(5)["id"] == 5
    assert repo.get_by_fdc_id(555)["fdc_id"] == 555


def test_search_by_name_returns_rows(patched_session):
    patched_session.execute.return_value.scalars.return_value.all.return_value = [
        _fake_row(id=1, name="A"),
        _fake_row(id=2, name="B"),
    ]
    repo = FoodReferenceRepository()
    rows = repo.search_by_name("pp", region="global", limit=5)
    assert len(rows) == 2
    assert rows[0]["name"] == "A"


def test_search_by_name_returns_empty_on_error(patched_session):
    patched_session.execute.side_effect = OSError("boom")
    repo = FoodReferenceRepository()
    assert repo.search_by_name("x") == []


def test_upsert_commits(patched_session):
    repo = FoodReferenceRepository()
    repo.upsert(
        {
            "barcode": "b1",
            "name": "N",
            "protein_100g": 1.0,
            "carbs_100g": 2.0,
            "fat_100g": 3.0,
        }
    )
    patched_session.execute.assert_called_once()
    patched_session.commit.assert_called_once()
    patched_session.close.assert_called_once()


def test_upsert_rollbacks_on_error(patched_session):
    patched_session.execute.side_effect = ValueError("dup")
    repo = FoodReferenceRepository()
    repo.upsert({"barcode": "b1", "name": "N"})
    patched_session.rollback.assert_called_once()


def test_upsert_seed_updated_when_barcode_exists(patched_session):
    existing = MagicMock()
    first_result = MagicMock()
    first_result.scalars.return_value.first.return_value = existing
    patched_session.execute.return_value = first_result
    repo = FoodReferenceRepository()
    status = repo.upsert_seed(
        {
            "barcode": "b1",
            "name_vi": "Táo",
            "source": "seed",
            "region": "VN",
            "unknown_column": "ignored",
        }
    )
    assert status == "updated"
    patched_session.commit.assert_called_once()


def test_upsert_seed_inserted_when_new(patched_session):
    first_result = MagicMock()
    first_result.scalars.return_value.first.return_value = None
    patched_session.execute.return_value = first_result
    repo = FoodReferenceRepository()
    status = repo.upsert_seed(
        {
            "barcode": "new",
            "name": "Apple",
            "name_vi": "Táo",
            "source": "seed",
            "region": "VN",
        }
    )
    assert status == "inserted"
    patched_session.add.assert_called_once()
    patched_session.commit.assert_called_once()


def test_upsert_seed_lookup_by_name_vi_when_no_barcode(patched_session):
    first_result = MagicMock()
    first_result.scalars.return_value.first.return_value = None
    patched_session.execute.return_value = first_result
    repo = FoodReferenceRepository()
    repo.upsert_seed(
        {
            "name": "Phở",
            "name_vi": "Phở",
            "source": "manual",
            "region": "VN",
        }
    )
    # Second part of branch: composite where without barcode
    patched_session.execute.assert_called()


def test_upsert_seed_skipped_on_exception(patched_session):
    patched_session.execute.side_effect = RuntimeError("fail")
    repo = FoodReferenceRepository()
    assert (
        repo.upsert_seed({"barcode": "b", "name_vi": "x", "source": "s"})
        == "skipped"
    )
    patched_session.rollback.assert_called_once()


def test_upsert_seed_truncates_long_category(patched_session):
    existing = MagicMock()
    first_result = MagicMock()
    first_result.scalars.return_value.first.return_value = existing
    patched_session.execute.return_value = first_result
    repo = FoodReferenceRepository()
    long_cat = "x" * 150
    repo.upsert_seed(
        {"barcode": "b", "category": long_cat, "name_vi": "n", "source": "s"}
    )
    assert len(existing.category) == 100


def test_to_dict_static():
    m = _fake_row()
    d = FoodReferenceRepository._to_dict(m)
    assert d["barcode"] == "123"
    assert d["protein_100g"] == 0.1
