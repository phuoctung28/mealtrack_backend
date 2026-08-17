"""Deterministic ranking helpers for public catalog browsing."""

from __future__ import annotations

import unicodedata

from src.app.services.catalog_meal_snapshot_service import CatalogMealSnapshot
from src.domain.model.meal_recommendation import CatalogMeal
from src.domain.services.meal_recommendation.plan_diversity_reranking_service import (
    SHORTLIST_LIMIT,
    PlanDiversityRerankingService,
)
from src.domain.services.meal_recommendation.recipe_scoring_service import RecipeScore


class CatalogPopularityUnavailableError(Exception):
    """Raised when no curated popularity rank has been seeded."""


def filter_meals(
    meals: tuple[CatalogMeal, ...],
    query: str | None,
    cuisine: str | None,
    meal_type: str | None,
) -> list[CatalogMeal]:
    normalized_query = normalize(query)
    normalized_cuisine = normalize(cuisine)
    return [
        meal
        for meal in meals
        if meal.calories > 0
        and (meal_type is None or meal_type in meal.meal_types)
        and (not normalized_cuisine or normalize(meal.cuisine) == normalized_cuisine)
        and (
            not normalized_query
            or normalized_query in normalize(meal.name)
            or normalized_query in normalize(meal.cuisine)
        )
    ]


def rank_popular(
    meals: list[CatalogMeal], *, popularity_configured: bool
) -> list[CatalogMeal]:
    if not popularity_configured or any(meal.popularity_rank is None for meal in meals):
        raise CatalogPopularityUnavailableError
    return sorted(
        meals,
        key=lambda meal: (
            meal.popularity_rank,
            normalize(meal.name),
            meal.id,
        ),
    )


def diversity_rank(
    ranked_scores: list[RecipeScore],
    diversity: PlanDiversityRerankingService,
    snapshot: CatalogMealSnapshot,
) -> list[CatalogMeal]:
    selected: list[RecipeScore] = []
    remaining = ranked_scores[:]
    while remaining and len(selected) < SHORTLIST_LIMIT:
        reranked = diversity.rerank_shortlist(
            remaining,
            comparison_meals=tuple(item.catalog_meal for item in selected),
            ingredient_statistics=snapshot.ingredient_statistics,
        )
        winner = reranked[0]
        selected.append(winner)
        remaining = [
            item for item in remaining if item.catalog_meal.id != winner.catalog_meal.id
        ]
    return [item.catalog_meal for item in selected] + [
        item.catalog_meal for item in remaining
    ]


def normalize(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").split()).casefold()
