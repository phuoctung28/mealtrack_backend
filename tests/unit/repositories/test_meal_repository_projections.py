"""Tests that MealRepository projection parameter controls relationship loading."""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

from src.domain.model import FoodItem, Macros, Meal, MealImage, MealStatus, Nutrition
from src.infra.database.models.enums import MealStatusEnum
from src.infra.database.models.meal.meal import MealORM
from src.infra.database.models.meal.meal_image import MealImageORM
from src.infra.database.models.nutrition.nutrition import NutritionORM
from src.infra.repositories.meal_repository import MealProjection, MealRepository


def _make_repo():
    session = MagicMock()
    query = session.query.return_value
    options = query.options.return_value
    date_query = options.filter.return_value.filter.return_value.filter.return_value
    date_query.order_by.return_value.limit.return_value.all.return_value = []
    options.filter.return_value.first.return_value = None
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


def test_date_range_skips_ready_rows_without_required_domain_data(test_session):
    """Malformed legacy READY rows must not crash summary/feed queries."""
    repository = MealRepository(test_session)
    user_id = str(uuid.uuid4())
    target_date = date.today()
    created_at = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)

    invalid_meal_id = str(uuid.uuid4())
    valid_meal_id = str(uuid.uuid4())
    invalid_image_id = str(uuid.uuid4())
    valid_image_id = str(uuid.uuid4())

    test_session.add_all(
        [
            MealImageORM(
                image_id=invalid_image_id,
                format="jpeg",
                size_bytes=1,
                url="https://example.com/invalid.jpg",
            ),
            MealImageORM(
                image_id=valid_image_id,
                format="jpeg",
                size_bytes=1,
                url="https://example.com/valid.jpg",
            ),
            MealORM(
                meal_id=invalid_meal_id,
                user_id=user_id,
                status=MealStatusEnum.READY,
                image_id=invalid_image_id,
                created_at=created_at,
                updated_at=created_at,
                ready_at=created_at,
                dish_name="Missing Nutrition",
            ),
            MealORM(
                meal_id=valid_meal_id,
                user_id=user_id,
                status=MealStatusEnum.READY,
                image_id=valid_image_id,
                created_at=created_at,
                updated_at=created_at,
                ready_at=created_at,
                dish_name="Complete Meal",
            ),
            NutritionORM(
                meal_id=valid_meal_id,
                protein=25.0,
                carbs=40.0,
                fat=12.0,
                confidence_score=0.95,
            ),
        ]
    )
    test_session.flush()

    meals = repository.find_by_date_range(user_id, target_date, target_date)

    assert [meal.meal_id for meal in meals] == [valid_meal_id]
    assert repository.get_daily_meal_counts(user_id, target_date, target_date) == {
        target_date: 1
    }
