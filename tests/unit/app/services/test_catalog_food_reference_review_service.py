import pytest

from src.app.services.catalog_food_reference_review_service import (
    CatalogFoodReferenceReviewService,
)
from src.domain.ports.food_reference_repository_port import (
    FoodReferenceNutritionProjection,
)


class _FoodReferences:
    def __init__(self, reference):
        self.reference = reference
        self.approved_ids = []

    async def approve_for_catalog_seed(self, food_reference_id):
        self.approved_ids.append(food_reference_id)
        return self.reference


def _reference():
    return FoodReferenceNutritionProjection(
        id=42,
        name="Rice noodles, cooked",
        source="fatsecret",
        is_verified=True,
        protein_100g=2.0,
        carbs_100g=25.0,
        fat_100g=0.2,
    )


@pytest.mark.asyncio
async def test_approve_marks_one_reviewed_reference_available_for_catalog_import():
    references = _FoodReferences(_reference())

    approval = await CatalogFoodReferenceReviewService(references).approve(42)

    assert references.approved_ids == [42]
    assert approval is not None
    assert approval.food_reference_id == 42
    assert approval.is_verified is True


@pytest.mark.asyncio
async def test_approve_returns_none_when_reference_is_missing():
    references = _FoodReferences(None)

    approval = await CatalogFoodReferenceReviewService(references).approve(404)

    assert references.approved_ids == [404]
    assert approval is None
