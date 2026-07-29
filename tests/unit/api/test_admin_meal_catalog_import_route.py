from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.base_dependencies import get_async_db
from src.api.dependencies.auth import require_admin_or_local
from src.api.routes.v1 import admin_meal_catalog_import as route_mod
from src.app.services.catalog_meal_seed_import_service import CatalogSeedImportSummary


def test_resolve_catalog_manifest_is_dry_run_and_does_not_commit(monkeypatch):
    db = AsyncMock()
    calls = []

    async def fake_run_importer(db_arg, request, *, dry_run):
        calls.append(dry_run)
        return CatalogSeedImportSummary(dry_run=dry_run, inserted=1)

    monkeypatch.setattr(route_mod, "_run_importer", fake_run_importer)
    client = _client(db)

    response = client.post("/v1/admin/meal-catalog/resolve", json=_request())

    assert response.status_code == 200
    assert response.json()["applied"] is False
    assert response.json()["dry_run"] is True
    assert calls == [True]
    db.commit.assert_not_awaited()


def test_import_catalog_manifest_previews_then_commits(monkeypatch):
    db = AsyncMock()
    calls = []

    async def fake_run_importer(db_arg, request, *, dry_run):
        calls.append(dry_run)
        return CatalogSeedImportSummary(dry_run=dry_run, inserted=1)

    monkeypatch.setattr(route_mod, "_run_importer", fake_run_importer)
    client = _client(db)

    response = client.post("/v1/admin/meal-catalog/import", json=_request())

    assert response.status_code == 200
    assert response.json()["applied"] is True
    assert response.json()["inserted"] == 1
    assert calls == [True, False]
    db.commit.assert_awaited_once()


def test_import_catalog_manifest_returns_validation_report_without_db_work():
    db = AsyncMock()
    client = _client(db)
    payload = _request()
    payload["manifest"]["recipes"][0]["meal_types"] = []

    response = client.post("/v1/admin/meal-catalog/import", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["validation"]["errors"]
    db.commit.assert_not_awaited()


def _client(db):
    app = FastAPI()
    app.include_router(route_mod.router)
    app.dependency_overrides[get_async_db] = lambda: db
    app.dependency_overrides[require_admin_or_local] = lambda: "admin@nutree.ai"
    return TestClient(app)


def _request():
    return {
        "manifest": {
            "release_key": "test-release",
            "expected_recipe_count": 1,
            "recipes": [
                {
                    "recipe_key": "pho-ga-001",
                    "cuisine": "vietnamese",
                    "name": "Pho Ga",
                    "meal_types": ["lunch"],
                    "ingredients": [
                        {
                            "food_reference_id": 1,
                            "name": "Chicken breast",
                            "quantity": 120,
                            "unit": "g",
                        }
                    ],
                }
            ],
        },
        "partial": True,
        "min_per_cuisine_meal_type": 0,
    }
