"""Admin review service for food references used by catalog imports."""

from dataclasses import dataclass

from src.domain.ports.food_reference_repository_port import (
    FoodReferenceNutritionProjection,
    FoodReferenceRepositoryPort,
)


@dataclass(frozen=True)
class CatalogFoodReferenceApproval:
    """The reference an administrator approved for catalog publication."""

    food_reference_id: int
    name: str
    source: str
    is_verified: bool


class CatalogFoodReferenceReviewService:
    """Makes an explicit admin decision durable before catalog publication."""

    def __init__(self, food_references: FoodReferenceRepositoryPort):
        self._food_references = food_references

    async def approve(
        self,
        food_reference_id: int,
    ) -> CatalogFoodReferenceApproval | None:
        """Approve a reviewed reference, returning ``None`` when it no longer exists."""

        reference = await self._food_references.approve_for_catalog_seed(
            food_reference_id
        )
        if reference is None:
            return None
        return _approval(reference)


def _approval(
    reference: FoodReferenceNutritionProjection,
) -> CatalogFoodReferenceApproval:
    return CatalogFoodReferenceApproval(
        food_reference_id=reference.id,
        name=reference.name,
        source=reference.source,
        is_verified=reference.is_verified,
    )
