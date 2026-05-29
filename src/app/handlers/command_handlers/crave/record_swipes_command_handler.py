import uuid

from src.app.commands.crave.record_swipes_command import RecordSwipesCommand
from src.app.events.base import EventHandler
from src.app.events.crave.meal_swiped_event import MealSwipedEvent
from src.infra.database.config import ScopedSession
from src.infra.database.uow import UnitOfWork
from src.infra.repositories.crave.crave_seen_repository import CraveSeenRepository
from src.infra.repositories.crave.meal_catalog_repository import MealCatalogRepository
from src.infra.repositories.crave.swipe_event_repository import SwipeEventRepository
from src.infra.repositories.saved_suggestion_db_repository import (
    SavedSuggestionDbRepository,
)

_STAT = {
    "save": {"saved": 1},
    "cook": {"cooked": 1},
    "skip": {"skipped": 1},
}


class RecordSwipesCommandHandler(EventHandler[RecordSwipesCommand, None]):
    def __init__(
        self,
        *,
        swipe_repo=None,
        catalog_repo=None,
        saved_repo=None,
        seen_repo=None,
        bus=None,
        uow=None,
    ) -> None:
        self._swipes = swipe_repo
        self._catalog = catalog_repo
        self._saved = saved_repo
        self._seen = seen_repo
        self._bus = bus
        self._uow = uow

    def _deps(self):
        if all([self._swipes, self._catalog, self._saved, self._seen, self._uow]):
            return self._swipes, self._catalog, self._saved, self._seen, self._uow
        session = ScopedSession()
        return (
            self._swipes or SwipeEventRepository(session),
            self._catalog or MealCatalogRepository(session),
            self._saved or SavedSuggestionDbRepository(session),
            self._seen or CraveSeenRepository(session),
            self._uow or UnitOfWork(session),
        )

    async def handle(self, command: RecordSwipesCommand) -> None:
        swipes_repo, catalog, saved, seen, uow = self._deps()
        rows = [
            {
                "id": f"sw_{uuid.uuid4().hex}",
                "user_id": command.user_id,
                "catalog_meal_id": swipe.catalog_meal_id,
                "deck_id": command.deck_id,
                "direction": swipe.direction,
                "position": swipe.position,
                "dwell_ms": swipe.dwell_ms,
                "meal_type": swipe.meal_type,
            }
            for swipe in command.swipes
        ]
        with uow:
            swipes_repo.bulk_insert(rows)
            for swipe in command.swipes:
                catalog.increment_stats(
                    swipe.catalog_meal_id,
                    shown=1,
                    **_STAT.get(swipe.direction, {}),
                )
                if swipe.direction == "save":
                    meal = catalog.get(swipe.catalog_meal_id)
                    if meal is not None:
                        saved.upsert_from_catalog(command.user_id, meal)
            seen.mark_seen(
                command.user_id, [swipe.catalog_meal_id for swipe in command.swipes]
            )
            uow.commit()

        if self._bus is not None:
            for swipe in command.swipes:
                await self._bus.publish(
                    MealSwipedEvent(
                        user_id=command.user_id,
                        catalog_meal_id=swipe.catalog_meal_id,
                        direction=swipe.direction,
                        meal_type=swipe.meal_type,
                    )
                )
