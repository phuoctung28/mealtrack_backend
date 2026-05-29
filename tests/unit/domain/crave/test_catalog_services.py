import pytest

from src.domain.services.crave.catalog_coverage_service import CatalogCoverageService
from src.domain.services.crave.catalog_generation_service import (
    CatalogGenerationService,
    GenSpec,
)
from src.domain.services.crave.recipe_macro_computer import ComputedMacros


class FakeStructureGen:
    async def generate(self, spec, count):
        return [
            {
                "meal_name": "Veg Bowl",
                "ingredients": [{"name": "tofu", "grams": 150}],
                "cuisine": "japanese",
                "dietary_flags": ["vegan"],
                "allergen_flags": ["soy"],
                "tags": ["high_protein"],
                "meal_types": ["lunch"],
            }
        ]


class FakeMacroComputer:
    async def compute(self, ingredients):
        return ComputedMacros(520, 40, 48, 16, 6, 1.0)


class FakeImages:
    async def resolve(self, name):
        return ("http://img/x.jpg", "http://img/t.jpg")


class FakeEmbedder:
    async def embed(self, text):
        return [0.1] * 512


class FakeRepo:
    def __init__(self):
        self.rows = []

    def exists_similar(self, name, embedding):
        return False

    def upsert(self, data):
        self.rows.append(data)


@pytest.mark.asyncio
async def test_generates_and_upserts_with_verified_macros():
    repo = FakeRepo()
    service = CatalogGenerationService(
        structure_gen=FakeStructureGen(),
        macro_computer=FakeMacroComputer(),
        images=FakeImages(),
        embedder=FakeEmbedder(),
        repo=repo,
    )

    count = await service.generate_for(
        GenSpec(meal_type="lunch", cuisine="japanese", calorie_band=500),
        count=1,
    )

    assert count == 1
    assert repo.rows[0]["calories"] == 520
    assert repo.rows[0]["calorie_band"] == 500
    assert repo.rows[0]["allergen_flags"] == ["soy"]
    assert "embedding" in repo.rows[0]
    assert repo.rows[0]["recipe_status"] == "none"


@pytest.mark.asyncio
async def test_rejects_meal_when_macros_unverified():
    class NullMacro:
        async def compute(self, ingredients):
            return None

    repo = FakeRepo()
    service = CatalogGenerationService(
        structure_gen=FakeStructureGen(),
        macro_computer=NullMacro(),
        images=FakeImages(),
        embedder=FakeEmbedder(),
        repo=repo,
    )

    count = await service.generate_for(
        GenSpec(meal_type="lunch", cuisine="japanese", calorie_band=500),
        count=1,
    )

    assert count == 0
    assert repo.rows == []


def test_finds_underfilled_cells():
    counts = {("lunch", "japanese", 500): 2, ("lunch", "italian", 500): 0}
    service = CatalogCoverageService(
        meal_types=["lunch"],
        cuisines=["japanese", "italian"],
        bands=[500],
        target_per_cell=10,
    )

    gaps = service.find_gaps(counts)
    cells = {(g.meal_type, g.cuisine, g.calorie_band): g for g in gaps}

    assert cells[("lunch", "italian", 500)].needed == 10
    assert cells[("lunch", "japanese", 500)].needed == 8
