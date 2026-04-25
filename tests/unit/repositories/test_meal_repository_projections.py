"""Tests that MealRepository projection parameter controls relationship loading."""

from unittest.mock import MagicMock
from datetime import date
from datetime import datetime
import uuid

import pytest

from src.infra.repositories.meal_repository import MealRepository, MealProjection
from src.domain.model import Meal, MealStatus, MealImage, Nutrition, Macros, FoodItem


def _make_repo():
    session = MagicMock()
    session.query.return_value.options.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
        []
    )
    session.query.return_value.options.return_value.filter.return_value.first.return_value = (
        None
    )
    return MealRepository(session)


def test_meal_projection_enum_exists():
    """MealProjection enum must have MACROS_ONLY, FULL, FULL_WITH_TRANSLATIONS."""
    assert hasattr(MealProjection, "MACROS_ONLY")
    assert hasattr(MealProjection, "FULL")
    assert hasattr(MealProjection, "FULL_WITH_TRANSLATIONS")


def test_find_by_date_accepts_projection_parameter():
    """find_by_date must accept a projection keyword argument without error."""
    repo = _make_repo()
    # Should not raise TypeError
    repo.find_by_date(
        date(2026, 4, 18), user_id="u1", projection=MealProjection.MACROS_ONLY
    )


def test_find_by_id_accepts_projection_parameter():
    """find_by_id must accept a projection keyword argument without error."""
    repo = _make_repo()
    repo.find_by_id("meal-1", projection=MealProjection.FULL_WITH_TRANSLATIONS)


def test_projection_opt_counts():
    """Each projection must have the correct number of load options."""
    from src.infra.repositories.meal_repository import _PROJECTION_OPTS, MealProjection

    # MACROS_ONLY: noload(image) + nutrition chain selectinload
    assert (
        len(_PROJECTION_OPTS[MealProjection.MACROS_ONLY]) == 2
    ), "MACROS_ONLY must have 2 load options (noload image, nutrition chain)"
    # FULL: image + nutrition chain
    assert (
        len(_PROJECTION_OPTS[MealProjection.FULL]) == 2
    ), "FULL must have 2 load options (image, nutrition chain)"
    # FULL_WITH_TRANSLATIONS: image + nutrition chain + translations
    assert (
        len(_PROJECTION_OPTS[MealProjection.FULL_WITH_TRANSLATIONS]) == 3
    ), "FULL_WITH_TRANSLATIONS must have 3 load options (image, nutrition chain, translations)"


def test_save_new_meal_inserts_food_items_once(test_session):
    """Saving a new meal should not duplicate nested nutrition/food_items inserts."""
    repository = MealRepository(test_session)

    meal = Meal(
        meal_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        status=MealStatus.READY,
        created_at=datetime.now(),
        image=MealImage(
            image_id=str(uuid.uuid4()),
            format="jpeg",
            size_bytes=1,
            url="https://example.com/test.jpg",
        ),
        dish_name="Empanadas",
        nutrition=Nutrition(
            macros=Macros(protein=20.0, carbs=30.0, fat=10.0),
            food_items=[
                FoodItem(
                    id=str(uuid.uuid4()),
                    name="Flour",
                    quantity=100.0,
                    unit="g",
                    macros=Macros(protein=10.0, carbs=20.0, fat=2.0),
                    is_custom=True,
                ),
                FoodItem(
                    id=str(uuid.uuid4()),
                    name="Beef",
                    quantity=120.0,
                    unit="g",
                    macros=Macros(protein=10.0, carbs=10.0, fat=8.0),
                    is_custom=True,
                ),
            ],
            confidence_score=0.9,
        ),
        ready_at=datetime.now(),
    )

    repository.save(meal)

    from src.infra.database.models.nutrition.food_item import FoodItemORM

    inserted_items = (
        test_session.query(FoodItemORM)
        .filter(FoodItemORM.nutrition_id.isnot(None))
        .all()
    )
    assert len(inserted_items) == 2
