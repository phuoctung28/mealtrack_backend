from decimal import Decimal

from src.app.services.catalog_meal_insight_scheduler import (
    schedule_catalog_import_insights,
)
from src.domain.model.meal_recommendation import CatalogMeal


def _meal() -> CatalogMeal:
    return CatalogMeal(
        id="catalog-1",
        catalog_key="key-1",
        content_hash="a" * 64,
        name="Egg Rice",
        cuisine="Japanese",
        description=None,
        image_url=None,
        protein_g=Decimal("20"),
        carbs_g=Decimal("40"),
        fat_g=Decimal("10"),
        fiber_g=Decimal("2"),
        meal_types=("breakfast",),
    )


def test_schedule_catalog_import_insights_spawns_language_tasks():
    manager = SimpleTaskManager()
    scheduled = schedule_catalog_import_insights(
        manager,
        [_meal()],
        cache_service=object(),
        ai_manager=object(),
        languages=frozenset({"en", "vi"}),
    )
    assert scheduled == 2
    assert set(manager.names) == {
        "catalog-meal-insights:catalog-1:en",
        "catalog-meal-insights:catalog-1:vi",
    }


def test_schedule_catalog_import_insights_skips_without_prereqs():
    assert (
        schedule_catalog_import_insights(
            None,
            [_meal()],
            cache_service=object(),
            ai_manager=object(),
        )
        == 0
    )


class SimpleTaskManager:
    def __init__(self):
        self.names = []

    def spawn(self, name, coro):
        self.names.append(name)
        close = getattr(coro, "close", None)
        if close is not None:
            close()
        return name
