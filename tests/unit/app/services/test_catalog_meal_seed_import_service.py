from types import SimpleNamespace

import pytest

from src.app.services.catalog_meal_seed_import_service import (
    CatalogMealSeedImporter,
    CatalogSeedResolutionCandidate,
)
from src.domain.ports.food_reference_repository_port import (
    FoodReferenceNutritionProjection,
)


class _Session:
    def __init__(self):
        self.added = []
        self.flushed = False

    def add(self, row):
        self.added.append(row)

    async def flush(self):
        self.flushed = True


class _Importer(CatalogMealSeedImporter):
    def __init__(
        self,
        *,
        refs_by_id=None,
        refs_by_name=None,
        existing=None,
        candidates=None,
        approved_mappings=None,
        auto_resolve_threshold=0.92,
        resolve_all_best_effort=False,
    ):
        self.session = _Session()
        super().__init__(
            self.session,
            approved_mappings=approved_mappings,
            auto_resolve_threshold=auto_resolve_threshold,
            resolve_all_best_effort=resolve_all_best_effort,
        )
        self.refs_by_id = refs_by_id or {}
        self.refs_by_name = refs_by_name or {}
        self.existing = existing
        self.candidates = candidates or []

    async def _get_reference_by_id(self, food_reference_id):
        if food_reference_id in self.refs_by_id:
            return self.refs_by_id[food_reference_id]
        for refs in self.refs_by_name.values():
            for ref in refs:
                if ref.id == food_reference_id:
                    return ref
        return None

    async def _find_reference_candidates_by_normalized_name(self, name_normalized):
        return [
            CatalogSeedResolutionCandidate(
                food_reference_id=ref.id,
                name=ref.name,
                name_normalized=name_normalized,
                source=ref.source,
                is_verified=ref.is_verified,
                score=1.0,
            )
            for ref in self.refs_by_name.get(name_normalized, [])
        ]

    async def _find_existing(self, catalog_key, content_hash):
        if self.existing == "exact":
            return SimpleNamespace(catalog_key=catalog_key, content_hash=content_hash)
        if self.existing == "changed":
            return SimpleNamespace(catalog_key=catalog_key, content_hash="different")
        return None

    async def _ranked_candidates(self, normalized_name):
        return self.candidates


def _reference(food_reference_id=7, *, name="Rice", is_verified=True):
    return FoodReferenceNutritionProjection(
        id=food_reference_id,
        name=name,
        source="catalog_seed",
        is_verified=is_verified,
        protein_100g=2.7,
        carbs_100g=28.0,
        fat_100g=0.3,
        fiber_100g=0.4,
        sugar_100g=0.1,
        density_g_ml=1.0,
    )


def _manifest(*, food_reference_id=7):
    return {
        "recipes": [
            {
                "recipe_key": "vn-rice-breakfast",
                "cuisine": "vietnamese",
                "name": "Rice Breakfast",
                "meal_types": ["breakfast"],
                "ingredients": [
                    {
                        "food_reference_id": food_reference_id,
                        "name": "Rice",
                        "quantity": 100,
                        "unit": "g",
                    }
                ],
            }
        ]
    }


def _egg_manifest():
    manifest = _manifest(food_reference_id=None)
    manifest["recipes"][0]["ingredients"][0]["name"] = "Egg"
    manifest["recipes"][0]["ingredients"][0]["quantity"] = 1
    manifest["recipes"][0]["ingredients"][0]["unit"] = "each"
    return manifest


@pytest.mark.asyncio
async def test_import_inserts_catalog_meal_without_derived_nutrition_snapshots():
    importer = _Importer(refs_by_id={7: _reference()})

    summary = await importer.import_manifest(_manifest())

    assert summary.inserted == 1
    assert summary.skipped_existing == 0
    assert summary.errors == ()
    assert importer.session.flushed is True
    row = importer.session.added[0]
    assert row.catalog_key == "vn-rice-breakfast"
    assert row.breakfast_eligible is True
    assert not hasattr(row, "protein_g")
    assert not hasattr(row, "servings")
    assert row.ingredients[0].food_reference_id == 7
    assert row.ingredients[0].display_name == "Rice"
    assert not hasattr(row.ingredients[0], "resolved_grams")


@pytest.mark.asyncio
async def test_import_resolves_null_food_reference_id_by_normalized_name():
    importer = _Importer(refs_by_name={"rice": [_reference()]})

    summary = await importer.import_manifest(_manifest(food_reference_id=None))

    assert summary.inserted == 1
    assert summary.errors == ()
    assert importer.session.added[0].ingredients[0].food_reference_id == 7


@pytest.mark.asyncio
async def test_import_skips_exact_existing_catalog_meal():
    importer = _Importer(refs_by_id={7: _reference()}, existing="exact")

    summary = await importer.import_manifest(_manifest())

    assert summary.inserted == 0
    assert summary.skipped_existing == 1
    assert importer.session.added == []


@pytest.mark.asyncio
async def test_import_rejects_existing_catalog_key_with_changed_content():
    importer = _Importer(refs_by_id={7: _reference()}, existing="changed")

    summary = await importer.import_manifest(_manifest())

    assert summary.inserted == 0
    assert "catalog_key already exists with different content" in summary.errors[0]


@pytest.mark.asyncio
async def test_import_reports_unresolved_food_reference_candidates():
    importer = _Importer(
        candidates=[
            CatalogSeedResolutionCandidate(
                food_reference_id=1,
                name="White rice",
                name_normalized="white rice",
                source="catalog_seed",
                is_verified=True,
                score=0.7,
            ),
            CatalogSeedResolutionCandidate(
                food_reference_id=2,
                name="Brown rice",
                name_normalized="brown rice",
                source="catalog_seed",
                is_verified=True,
                score=0.6,
            ),
        ],
        auto_resolve_threshold=None,
    )

    summary = await importer.import_manifest(_manifest(food_reference_id=None))

    assert summary.inserted == 0
    assert "needs_review" in summary.errors[0]
    assert summary.resolution_issues[0].candidates[0].food_reference_id == 1
    assert summary.resolution_report()["issues"][0]["candidates"][0]["name"] == "White rice"


@pytest.mark.asyncio
async def test_import_uses_approved_mapping_for_null_food_reference_id():
    importer = _Importer(
        refs_by_id={8: _reference(8, name="White rice")},
        approved_mappings={"Rice": 8},
    )

    summary = await importer.import_manifest(_manifest(food_reference_id=None))

    assert summary.inserted == 1
    assert summary.errors == ()
    assert importer.session.added[0].ingredients[0].food_reference_id == 8


@pytest.mark.asyncio
async def test_import_auto_resolves_high_confidence_verified_candidate():
    importer = _Importer(
        refs_by_id={8: _reference(8, name="White rice")},
        candidates=[
            CatalogSeedResolutionCandidate(
                food_reference_id=8,
                name="White rice",
                name_normalized="white rice",
                source="catalog_seed",
                is_verified=True,
                score=0.96,
            )
        ],
    )

    summary = await importer.import_manifest(_manifest(food_reference_id=None))

    assert summary.inserted == 1
    assert summary.errors == ()
    assert importer.session.added[0].ingredients[0].food_reference_id == 8


@pytest.mark.asyncio
async def test_import_reports_unverified_exact_match():
    importer = _Importer(refs_by_name={"rice": [_reference(is_verified=False)]})

    summary = await importer.import_manifest(_manifest(food_reference_id=None))

    assert summary.inserted == 0
    assert "exact_match_not_verified" in summary.errors[0]
    assert summary.resolution_issues[0].candidates[0].is_verified is False


@pytest.mark.asyncio
async def test_import_best_effort_accepts_unverified_exact_match():
    importer = _Importer(
        refs_by_name={"rice": [_reference(is_verified=False)]},
        auto_resolve_threshold=0.0,
        resolve_all_best_effort=True,
    )

    summary = await importer.import_manifest(_manifest(food_reference_id=None))

    assert summary.inserted == 1
    assert summary.errors == ()


@pytest.mark.asyncio
async def test_import_best_effort_accepts_top_unverified_fuzzy_candidate():
    importer = _Importer(
        refs_by_id={8: _reference(8, name="White rice", is_verified=False)},
        candidates=[
            CatalogSeedResolutionCandidate(
                food_reference_id=8,
                name="White rice",
                name_normalized="white rice",
                source="fatsecret",
                is_verified=False,
                score=0.2,
            )
        ],
        auto_resolve_threshold=0.0,
        resolve_all_best_effort=True,
    )

    summary = await importer.import_manifest(_manifest(food_reference_id=None))

    assert summary.inserted == 1
    assert summary.errors == ()
    assert importer.session.added[0].ingredients[0].food_reference_id == 8


@pytest.mark.asyncio
async def test_import_best_effort_resolves_common_each_unit_for_egg():
    importer = _Importer(
        refs_by_name={"egg": [_reference(9, name="Egg", is_verified=False)]},
        auto_resolve_threshold=0.0,
        resolve_all_best_effort=True,
    )

    summary = await importer.import_manifest(_egg_manifest())

    assert summary.inserted == 1
    assert summary.errors == ()
    assert importer.session.added[0].ingredients[0].unit == "each"
