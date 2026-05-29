import pytest

from src.app.handlers.query_handlers.crave.get_crave_recipe_query_handler import (
    GetCraveRecipeQueryHandler,
)
from src.app.queries.crave.get_crave_recipe_query import GetCraveRecipeQuery


class Meal:
    def __init__(self):
        self.id = "a"
        self.recipe_status = "none"
        self.recipe_steps = None
        self.meal_name = "Bowl"
        self.ingredients = [{"name": "salmon", "grams": 150}]


class FakeRepo:
    def __init__(self):
        self.meal = Meal()

    def get(self, meal_id):
        return self.meal

    def save_recipe(self, meal_id, steps):
        self.meal.recipe_steps = steps
        self.meal.recipe_status = "ready"


class FakeGen:
    async def generate_recipe(self, meal):
        return ["Step 1", "Step 2"]


class FakeUow:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_lazy_generates_and_caches_recipe_on_first_request():
    repo = FakeRepo()
    handler = GetCraveRecipeQueryHandler(
        catalog_repo=repo, generator=FakeGen(), uow=FakeUow()
    )

    output = await handler.handle(GetCraveRecipeQuery(catalog_meal_id="a"))

    assert output["recipe_steps"] == ["Step 1", "Step 2"]
    assert repo.meal.recipe_status == "ready"


@pytest.mark.asyncio
async def test_served_from_cache_when_ready():
    repo = FakeRepo()
    repo.meal.recipe_status = "ready"
    repo.meal.recipe_steps = ["Cached"]
    called = {"count": 0}

    class Gen:
        async def generate_recipe(self, meal):
            called["count"] += 1
            return ["X"]

    handler = GetCraveRecipeQueryHandler(
        catalog_repo=repo, generator=Gen(), uow=FakeUow()
    )

    output = await handler.handle(GetCraveRecipeQuery(catalog_meal_id="a"))

    assert output["recipe_steps"] == ["Cached"]
    assert called["count"] == 0
