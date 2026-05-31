from typing import Any

from src.app.events.base import EventHandler
from src.app.queries.crave.get_crave_recipe_query import GetCraveRecipeQuery
from src.infra.database.config import ScopedSession
from src.infra.database.uow import UnitOfWork
from src.infra.repositories.crave.meal_catalog_repository import MealCatalogRepository


class SimpleRecipeGenerator:
    async def generate_recipe(self, meal) -> list[str]:
        ingredients = ", ".join(
            f"{item.get('grams')}g {item.get('name')}"
            for item in (meal.ingredients or [])
        )
        return [
            f"Prepare ingredients: {ingredients}.",
            "Cook components until done and season to taste.",
            "Plate and serve.",
        ]


class GetCraveRecipeQueryHandler(EventHandler[GetCraveRecipeQuery, dict[str, Any]]):
    def __init__(self, *, catalog_repo=None, generator=None, uow=None) -> None:
        self._catalog = catalog_repo
        self._generator = generator or SimpleRecipeGenerator()
        self._uow = uow

    def _deps(self):
        if self._catalog is not None and self._uow is not None:
            return self._catalog, self._uow
        session = ScopedSession()
        return (
            self._catalog or MealCatalogRepository(session),
            self._uow or UnitOfWork(session),
        )

    async def handle(self, query: GetCraveRecipeQuery) -> dict[str, Any]:
        catalog, uow = self._deps()
        meal = catalog.get(query.catalog_meal_id)
        if meal is None:
            raise ValueError(f"catalog meal not found: {query.catalog_meal_id}")
        if meal.recipe_status == "ready" and meal.recipe_steps:
            recipe = meal.recipe_steps
        else:
            recipe = await self._generator.generate_recipe(meal)
            with uow:
                catalog.save_recipe(meal.id, recipe)
                uow.commit()
        return {
            "id": meal.id,
            "meal_name": meal.meal_name,
            "ingredients": meal.ingredients,
            "recipe_steps": recipe,
        }
