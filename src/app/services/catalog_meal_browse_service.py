"""Read-only catalog browsing and deterministic feed ranking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any, Literal

from src.app.services.catalog_meal_browse_ranking import (
    CatalogPopularityUnavailableError,
    diversity_rank,
    filter_meals,
    rank_popular,
)
from src.app.services.catalog_meal_snapshot_service import CatalogMealSnapshot
from src.app.services.meal_recommendation_history_projector import (
    MealRecommendationHistoryProjector,
)
from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationCatalogUnavailableError,
)
from src.domain.model.meal_recommendation import CatalogMeal
from src.domain.services.meal_recommendation.calorie_allocation_policy import (
    CalorieAllocationPolicy,
)
from src.domain.services.meal_recommendation.plan_diversity_reranking_service import (
    PlanDiversityRerankingService,
)
from src.domain.services.meal_recommendation.recipe_scoring_service import (
    RecipeScoringService,
)


class CatalogFeed(StrEnum):
    POPULAR = "popular"
    FOR_YOU = "for_you"


@dataclass(frozen=True)
class CatalogBrowsePage:
    """Ranked, paginated catalog projection plus feed provenance."""

    items: tuple[CatalogMeal, ...]
    total: int
    feed: CatalogFeed
    ranking_source: Literal["curated", "personalized"]
    fallback: bool = False
    allergy_evaluated: bool = False


class CatalogMealBrowseService:
    """Compose snapshot reads and recommendation scoring without persistence."""

    def __init__(
        self,
        *,
        uow_factory,
        snapshot_service,
        history_projector: MealRecommendationHistoryProjector | None = None,
        allocation: CalorieAllocationPolicy | None = None,
        scoring: RecipeScoringService | None = None,
        diversity: PlanDiversityRerankingService | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._snapshot_service = snapshot_service
        self._history_projector = (
            history_projector or MealRecommendationHistoryProjector()
        )
        self._allocation = allocation or CalorieAllocationPolicy()
        self._scoring = scoring or RecipeScoringService()
        self._diversity = diversity or PlanDiversityRerankingService()

    async def list_meals(
        self,
        *,
        user_id: str,
        feed: CatalogFeed,
        limit: int,
        offset: int,
        query: str | None,
        cuisine: str | None,
        meal_type: str | None,
        daily_calories: int | None = None,
        start_date: date | None = None,
        timezone: str | None = None,
        shuffle_seed: str | None = None,
    ) -> CatalogBrowsePage:
        async with self._uow_factory() as uow:
            if feed is CatalogFeed.POPULAR:
                page = await uow.catalog_recipes.list_popular_page(
                    limit=limit,
                    offset=offset,
                    query=query,
                    cuisine=cuisine,
                    meal_type=meal_type,
                    shuffle_seed=shuffle_seed,
                )
                if not page.any_ranked or page.unranked_count > 0:
                    raise CatalogPopularityUnavailableError
                return CatalogBrowsePage(
                    items=page.items,
                    total=page.total,
                    feed=feed,
                    ranking_source="curated",
                    fallback=False,
                )
            snapshot = await self._get_snapshot(uow)
            candidates = filter_meals(snapshot.meals, query, cuisine, meal_type)
            popularity_configured = any(
                meal.popularity_rank is not None for meal in snapshot.meals
            )
            ranked, fallback = await self._rank_for_you(
                uow,
                snapshot,
                candidates,
                user_id=user_id,
                meal_type=meal_type,
                daily_calories=daily_calories,
                start_date=start_date,
                timezone=timezone,
                popularity_configured=popularity_configured,
            )
            return CatalogBrowsePage(
                items=tuple(ranked[offset : offset + limit]),
                total=len(ranked),
                feed=feed,
                ranking_source="personalized" if not fallback else "curated",
                fallback=fallback,
            )

    async def get_meal(self, catalog_id: str) -> CatalogMeal:
        """Load one catalog meal by id without rebuilding the browse snapshot."""

        async with self._uow_factory() as uow:
            meal = await uow.catalog_recipes.get_meal(catalog_id)
            if meal is None:
                raise KeyError(catalog_id)
            return meal

    async def _get_snapshot(self, uow: Any) -> CatalogMealSnapshot:
        try:
            return await self._snapshot_service.get_snapshot(uow)
        except MealRecommendationCatalogUnavailableError:
            raise
        except Exception as exc:
            raise MealRecommendationCatalogUnavailableError from exc

    async def _rank_for_you(
        self,
        uow: Any,
        snapshot: CatalogMealSnapshot,
        candidates: list[CatalogMeal],
        *,
        user_id: str,
        meal_type: str | None,
        daily_calories: int | None,
        start_date: date | None,
        timezone: str | None,
        popularity_configured: bool,
    ) -> tuple[list[CatalogMeal], bool]:
        if (
            not daily_calories
            or daily_calories <= 0
            or start_date is None
            or not timezone
        ):
            return rank_popular(
                candidates, popularity_configured=popularity_configured
            ), True
        affinity = await self._history_projector.build_affinity(
            uow,
            user_id=user_id,
            start_date=start_date,
            timezone=timezone,
        )
        if not affinity.weights:
            return rank_popular(
                candidates, popularity_configured=popularity_configured
            ), True

        scored = []
        for meal in candidates:
            eligible_types = (
                [meal_type] if meal_type is not None else list(meal.meal_types)
            )
            meal_scores = [
                self._scoring.score(
                    meal,
                    target_calories=self._allocation.target_for(
                        daily_calories, candidate_type
                    ),
                    affinity=affinity,
                    ingredient_statistics=snapshot.ingredient_statistics,
                )
                for candidate_type in eligible_types
                if candidate_type in meal.meal_types
            ]
            if meal_scores:
                scored.append(
                    sorted(
                        meal_scores,
                        key=lambda item: (-item.score, item.catalog_meal.id),
                    )[0]
                )
        ranked_scores = sorted(
            scored, key=lambda item: (-item.score, item.catalog_meal.id)
        )
        return diversity_rank(ranked_scores, self._diversity, snapshot), False
