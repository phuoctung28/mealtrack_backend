import pytest

from src.app.handlers.query_handlers.crave.get_crave_deck_query_handler import (
    GetCraveDeckQueryHandler,
)
from src.app.queries.crave.get_crave_deck_query import GetCraveDeckQuery


class Meal:
    def __init__(self, meal_id, calories):
        self.id = meal_id
        self.calories = calories
        self.cuisine = "japanese"
        self.tags = []
        self.meal_name = meal_id
        self.english_name = meal_id
        self.protein_g = 30
        self.carbs_g = 40
        self.fat_g = 15
        self.image_url = None
        self.thumbnail_url = None
        self.allergen_flags = []
        self.dietary_flags = []


class FakeCatalogRepo:
    def __init__(self, meals):
        self.meals = meals

    def fetch_by_taste(self, **kwargs):
        return [meal for meal in self.meals if meal.id not in kwargs["exclude_ids"]]


class FakeSeen:
    def seen_ids(self, user_id):
        return ["seen1"]

    def mark_seen(self, user_id, ids):
        self.marked = ids


class FakeProfileRepo:
    def get_or_create(self, user_id):
        class Profile:
            taste_embedding = None
            cuisine_affinity = {"japanese": 0.8}
            ingredient_affinity = {}
            tag_affinity = {}

        return Profile()


class FakeBudget:
    def target_for(self, user_id, meal_type):
        return 540


class FakeCache:
    def __init__(self):
        self.store = {}

    async def get_json(self, key):
        return self.store.get(key)

    async def set_json(self, key, value, ttl):
        self.store[key] = value


@pytest.mark.asyncio
async def test_deck_ranked_excludes_seen_and_caches():
    handler = GetCraveDeckQueryHandler(
        catalog_repo=FakeCatalogRepo(
            [Meal("a", 520), Meal("b", 800), Meal("seen1", 530)]
        ),
        seen_repo=FakeSeen(),
        profile_repo=FakeProfileRepo(),
        budget=FakeBudget(),
        cache=FakeCache(),
    )

    result = await handler.handle(
        GetCraveDeckQuery(user_id="u1", meal_type="lunch", deck_size=10, is_paid=True)
    )

    ids = [card["id"] for card in result["meals"]]
    assert "seen1" not in ids
    assert ids[0] == "a"
    assert result["meals"][0]["match"] > 0
    assert "reason" in result["meals"][0]
