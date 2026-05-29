import pytest

from src.app.events.crave.meal_swiped_event import MealSwipedEvent
from src.app.handlers.event_handlers.taste_profile_update_handler import (
    TasteProfileUpdateHandler,
)


class Profile:
    def __init__(self):
        self.cuisine_affinity = {}
        self.ingredient_affinity = {}
        self.tag_affinity = {}
        self.taste_embedding = None
        self.swipe_count = 0
        self.user_id = "u1"


class FakeProfileRepo:
    def __init__(self):
        self.profile = Profile()

    def get_or_create(self, user_id):
        return self.profile

    def save(self, profile):
        self.saved = profile


class FakeCatalogRepo:
    def get(self, meal_id):
        class Meal:
            id = meal_id
            cuisine = "japanese"
            tags = ["high_protein"]
            ingredients = [{"name": "salmon"}]
            embedding = [0.1] * 512

        return Meal()


class FakeUow:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_save_event_updates_cuisine_affinity_and_commits():
    profiles = FakeProfileRepo()
    uow = FakeUow()
    handler = TasteProfileUpdateHandler(
        profile_repo=profiles,
        catalog_repo=FakeCatalogRepo(),
        uow=uow,
    )

    await handler.handle(
        MealSwipedEvent(
            user_id="u1",
            catalog_meal_id="a",
            direction="save",
            meal_type="lunch",
        )
    )

    assert profiles.profile.cuisine_affinity.get("japanese", 0) > 0
    assert profiles.profile.swipe_count == 1
    assert uow.committed
