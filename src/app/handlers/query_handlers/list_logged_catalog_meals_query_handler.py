"""List unique catalog meals the current user has logged."""

from __future__ import annotations

from src.api.mappers.catalog_meal_mapper import catalog_meal_browse_response
from src.app.events.base import EventHandler, handles
from src.app.queries.meal_catalog import ListLoggedCatalogMealsQuery
from src.domain.model.meal_recommendation import CatalogMeal


@handles(ListLoggedCatalogMealsQuery)
class ListLoggedCatalogMealsQueryHandler(
    EventHandler[ListLoggedCatalogMealsQuery, list[CatalogMeal]]
):
    def __init__(self, uow_factory, snapshot_service) -> None:
        self._uow_factory = uow_factory
        self._snapshot_service = snapshot_service

    async def handle(self, query: ListLoggedCatalogMealsQuery) -> list[CatalogMeal]:
        async with self._uow_factory() as uow:
            rows = await uow.meals.list_logged_catalog_meal_ids(
                user_id=query.user_id,
                limit=query.limit,
            )
            snapshot = await self._snapshot_service.get_snapshot(uow)
        by_id = {meal.id: meal for meal in snapshot.meals}
        return [by_id[catalog_id] for catalog_id, _logged_at in rows if catalog_id in by_id]


def to_logged_item_responses(meals: list[CatalogMeal]):
    return [
        catalog_meal_browse_response(meal).model_copy(update={"ingredients": []})
        for meal in meals
    ]
