"""Repository port for immutable catalog recipe projections."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.model.meal_recommendation.catalog_recipe import (
    CatalogRecipeVersion,
    CatalogRelease,
)


class CatalogRecipeRepositoryPort(ABC):
    """Read-side contract for published catalog recipes."""

    @abstractmethod
    async def get_active_release(self) -> CatalogRelease | None:
        """Return the active catalog release, if one is activated."""

    @abstractmethod
    async def list_active_versions(
        self,
        *,
        cuisine: str | None = None,
        meal_type: str | None = None,
    ) -> list[CatalogRecipeVersion]:
        """Return published versions visible through the active release."""

    @abstractmethod
    async def get_version(self, version_id: str) -> CatalogRecipeVersion | None:
        """Return one published catalog recipe version."""

