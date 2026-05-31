from typing import Any

from src.app.events.base import EventHandler
from src.app.queries.crave.get_crave_deck_query import GetCraveDeckQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.services.crave.crave_ranking_service import (
    CraveRankingService,
    RankInputs,
)
from src.infra.database.config import ScopedSession
from src.infra.repositories.crave.crave_seen_repository import CraveSeenRepository
from src.infra.repositories.crave.meal_catalog_repository import MealCatalogRepository
from src.infra.repositories.crave.taste_profile_repository import TasteProfileRepository

FREE_PREVIEW_SIZE = 8


def _band(target: int) -> int:
    return int(round(target / 100.0) * 100)


class CraveBudgetService:
    def target_for(self, user_id: str, meal_type: str) -> int:
        return 540


class GetCraveDeckQueryHandler(EventHandler[GetCraveDeckQuery, dict[str, Any]]):
    def __init__(
        self,
        *,
        catalog_repo=None,
        seen_repo=None,
        profile_repo=None,
        budget=None,
        cache=None,
        ranking: CraveRankingService | None = None,
    ) -> None:
        self._catalog = catalog_repo
        self._seen = seen_repo
        self._profiles = profile_repo
        self._budget = budget or CraveBudgetService()
        self._cache = cache
        self._ranking = ranking or CraveRankingService()

    def _deps(self):
        if self._catalog and self._seen and self._profiles:
            return self._catalog, self._seen, self._profiles, None
        session = ScopedSession()
        return (
            self._catalog or MealCatalogRepository(session),
            self._seen or CraveSeenRepository(session),
            self._profiles or TasteProfileRepository(session),
            session,
        )

    async def handle(self, query: GetCraveDeckQuery) -> dict[str, Any]:
        cache_key, ttl = CacheKeys.crave_deck(query.user_id, query.meal_type)
        if self._cache:
            cached = await self._cache.get_json(cache_key)
            if cached is not None:
                return cached

        catalog, seen_repo, profile_repo, session = self._deps()
        target = self._budget.target_for(query.user_id, query.meal_type)
        profile = profile_repo.get_or_create(query.user_id)
        seen = seen_repo.seen_ids(query.user_id) if query.is_paid else []
        candidates = catalog.fetch_by_taste(
            meal_type=query.meal_type,
            calorie_band=_band(target),
            embedding=getattr(profile, "taste_embedding", None),
            exclude_allergens=[],
            required_diet=[],
            exclude_ids=seen,
            limit=max(query.deck_size * 4, 40),
        )

        ranked = self._ranking.rank(
            candidates,
            RankInputs(
                target_calories=target,
                cuisine_affinity=getattr(profile, "cuisine_affinity", {}) or {},
                ingredient_affinity=getattr(profile, "ingredient_affinity", {}) or {},
                tag_affinity=getattr(profile, "tag_affinity", {}) or {},
                taste_cosine={},
                seen_ids=set(seen),
            ),
        )
        size = query.deck_size if query.is_paid else FREE_PREVIEW_SIZE
        meals = [
            {
                "id": item.meal.id,
                "meal_name": item.meal.meal_name,
                "english_name": item.meal.english_name,
                "calories": item.meal.calories,
                "protein_g": item.meal.protein_g,
                "carbs_g": item.meal.carbs_g,
                "fat_g": item.meal.fat_g,
                "image_url": item.meal.image_url,
                "thumbnail_url": item.meal.thumbnail_url,
                "match": item.match,
                "reason": item.reason,
                "locked": not query.is_paid,
            }
            for item in ranked[:size]
        ]
        if query.is_paid:
            seen_repo.mark_seen(query.user_id, [meal["id"] for meal in meals])
            if session is not None:
                session.commit()
        result = {
            "meal_type": query.meal_type,
            "target_calories": target,
            "meals": meals,
        }
        if self._cache:
            await self._cache.set_json(cache_key, result, ttl)
        return result
