import pytest

from src.app.commands.crave.record_swipes_command import RecordSwipesCommand, SwipeItem
from src.app.handlers.command_handlers.crave.record_swipes_command_handler import (
    RecordSwipesCommandHandler,
)


class FakeSwipeRepo:
    def __init__(self):
        self.rows = []

    def bulk_insert(self, rows):
        self.rows.extend(rows)


class FakeCatalogRepo:
    def __init__(self):
        self.stats = {}

    def increment_stats(self, meal_id, **kwargs):
        self.stats[meal_id] = kwargs

    def get(self, meal_id):
        class Meal:
            id = meal_id
            meal_type = "lunch"
            cuisine = "japanese"
            tags = []
            ingredients = []
            suggestion_data = None

        return Meal()


class FakeSavedRepo:
    def __init__(self):
        self.saved = []

    def upsert_from_catalog(self, user_id, meal):
        self.saved.append(meal.id)


class FakeSeen:
    def mark_seen(self, user_id, ids):
        self.marked = ids


class FakeBus:
    def __init__(self):
        self.published = []

    async def publish(self, event):
        self.published.append(event)


class FakeUow:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_records_events_saves_picks_and_emits_event():
    swipes = FakeSwipeRepo()
    catalog = FakeCatalogRepo()
    saved = FakeSavedRepo()
    bus = FakeBus()
    handler = RecordSwipesCommandHandler(
        swipe_repo=swipes,
        catalog_repo=catalog,
        saved_repo=saved,
        seen_repo=FakeSeen(),
        bus=bus,
        uow=FakeUow(),
    )

    await handler.handle(
        RecordSwipesCommand(
            user_id="u1",
            deck_id="d1",
            swipes=[
                SwipeItem(
                    catalog_meal_id="a",
                    direction="save",
                    position=0,
                    dwell_ms=900,
                    meal_type="lunch",
                ),
                SwipeItem(
                    catalog_meal_id="b",
                    direction="skip",
                    position=1,
                    dwell_ms=300,
                    meal_type="lunch",
                ),
            ],
        )
    )

    assert len(swipes.rows) == 2
    assert "a" in saved.saved
    assert "b" not in saved.saved
    assert len(bus.published) == 2
