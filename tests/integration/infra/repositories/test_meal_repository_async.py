"""Integration tests for AsyncMealRepository."""
import pytest
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.repositories.meal_repository_async import AsyncMealRepository
from src.infra.database.models.meal.meal import MealORM
from src.infra.database.models.meal.meal_image import MealImageORM
from src.infra.database.models.nutrition.nutrition import NutritionORM
from src.infra.database.models.nutrition.food_item import FoodItemORM
from src.infra.database.models.enums import MealStatusEnum


async def _insert_minimal_meal(session: AsyncSession, user_id: str, meal_id: str = "meal-001") -> MealORM:
    image = MealImageORM(
        image_id=f"img-{meal_id}",
        format="jpeg",
        size_bytes=1024,
        url="http://example.com/img.jpg",
    )
    session.add(image)
    await session.flush()

    nutrition = NutritionORM(
        meal_id=meal_id,
        protein=30.0,
        carbs=50.0,
        fat=10.0,
        fiber=5.0,
        sugar=2.0,
    )
    food_item = FoodItemORM(
        nutrition=nutrition,
        name="Chicken",
        protein=30.0,
        carbs=0.0,
        fat=5.0,
        fiber=0.0,
        sugar=0.0,
        quantity=150.0,
        unit="g",
        order_index=0,
    )
    meal = MealORM(
        meal_id=meal_id,
        user_id=user_id,
        status=MealStatusEnum.READY,
        image_id=f"img-{meal_id}",
    )
    meal.nutrition = nutrition
    session.add(meal)
    await session.flush()
    return meal


@pytest.mark.asyncio
async def test_find_by_id_returns_meal_with_nutrition(async_db_session):
    user_id = "user-async-01"
    await _insert_minimal_meal(async_db_session, user_id, "meal-async-01")

    repo = AsyncMealRepository(async_db_session)
    result = await repo.find_by_id("meal-async-01")

    assert result is not None
    assert result.meal_id == "meal-async-01"
    assert result.nutrition is not None
    assert result.nutrition.macros.protein == 30.0


@pytest.mark.asyncio
async def test_find_by_date_returns_meals_for_date(async_db_session):
    user_id = "user-async-02"
    await _insert_minimal_meal(async_db_session, user_id, "meal-async-02")

    repo = AsyncMealRepository(async_db_session)
    today = date.today()
    results = await repo.find_by_date(today, user_id=user_id)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_find_by_date_range_returns_meals(async_db_session):
    user_id = "user-async-03"
    await _insert_minimal_meal(async_db_session, user_id, "meal-async-03")

    repo = AsyncMealRepository(async_db_session)
    today = date.today()
    results = await repo.find_by_date_range(user_id, today, today)
    assert isinstance(results, list)
