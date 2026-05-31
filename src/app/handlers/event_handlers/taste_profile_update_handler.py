from src.app.events.crave.meal_swiped_event import MealSwipedEvent
from src.domain.services.crave.taste_profile_service import (
    SwipeSignal,
    TasteProfileService,
)
from src.infra.database.config import ScopedSession
from src.infra.database.uow import UnitOfWork
from src.infra.repositories.crave.meal_catalog_repository import MealCatalogRepository
from src.infra.repositories.crave.taste_profile_repository import TasteProfileRepository


class TasteProfileUpdateHandler:
    def __init__(
        self,
        *,
        profile_repo=None,
        catalog_repo=None,
        uow=None,
        service: TasteProfileService | None = None,
    ) -> None:
        self._profiles = profile_repo
        self._catalog = catalog_repo
        self._uow = uow
        self._service = service or TasteProfileService()

    def _deps(self):
        if self._profiles and self._catalog and self._uow:
            return self._profiles, self._catalog, self._uow
        session = ScopedSession()
        return (
            self._profiles or TasteProfileRepository(session),
            self._catalog or MealCatalogRepository(session),
            self._uow or UnitOfWork(session),
        )

    async def handle(self, event: MealSwipedEvent) -> None:
        profiles, catalog, uow = self._deps()
        meal = catalog.get(event.catalog_meal_id)
        if meal is None:
            return
        with uow:
            profile = profiles.get_or_create(event.user_id)
            updated = self._service.apply(
                {
                    "cuisine_affinity": profile.cuisine_affinity or {},
                    "ingredient_affinity": profile.ingredient_affinity or {},
                    "tag_affinity": profile.tag_affinity or {},
                },
                SwipeSignal(
                    direction=event.direction,
                    cuisine=getattr(meal, "cuisine", None),
                    tags=list(getattr(meal, "tags", []) or []),
                    ingredients=[
                        item.get("name")
                        for item in (getattr(meal, "ingredients", []) or [])
                        if item.get("name")
                    ],
                ),
            )
            profile.cuisine_affinity = updated["cuisine_affinity"]
            profile.ingredient_affinity = updated["ingredient_affinity"]
            profile.tag_affinity = updated["tag_affinity"]
            profile.swipe_count = (profile.swipe_count or 0) + 1
            if event.direction in ("save", "cook") and getattr(meal, "embedding", None):
                profile.taste_embedding = self._service.update_centroid(
                    profile.taste_embedding,
                    meal.embedding,
                    max(profile.swipe_count, 1),
                )
            profiles.save(profile)
            uow.commit()
