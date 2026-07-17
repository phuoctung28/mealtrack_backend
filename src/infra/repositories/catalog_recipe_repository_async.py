"""Async repository for curated catalog meal projections."""

from __future__ import annotations

from decimal import Decimal
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.model.meal_recommendation.catalog_recipe import (
    CatalogMeal,
    CatalogMealIngredient,
)
from src.domain.ports.catalog_recipe_repository_port import (
    CatalogMealRepositoryPort,
)
from src.domain.services.meal_recommendation.ingredient_quantity_conversion_service import (
    IngredientQuantityConversionService,
    ResolvedIngredientQuantity,
)
from src.infra.database.models.food_reference_model import FoodReferenceModel
from src.infra.database.models.meal_recommendation import (
    MealCatalogIngredientORM,
    MealCatalogORM,
)
from src.infra.repositories.food_reference_projection import (
    food_reference_model_to_nutrition_projection,
)

_CATALOG_CONVERTER = IngredientQuantityConversionService(
    allow_unverified=True,
    allow_unapproved_sources=True,
    allow_implausible_macros=True,
    allow_common_unit_fallbacks=True,
)


class AsyncCatalogMealRepository(CatalogMealRepositoryPort):
    """Repository for active catalog meals."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_active_meals(
        self,
        *,
        cuisine: str | None = None,
        meal_type: str | None = None,
    ) -> list[CatalogMeal]:
        stmt = (
            select(MealCatalogORM)
            .where(MealCatalogORM.is_active.is_(True))
            .options(_catalog_meal_load_options())
            .order_by(MealCatalogORM.id)
        )
        if cuisine is not None:
            stmt = stmt.where(MealCatalogORM.cuisine == cuisine)
        if meal_type is not None:
            column = _meal_type_column(meal_type)
            stmt = stmt.where(column.is_(True))

        result = await self._session.execute(stmt)
        return [_meal_to_domain(row) for row in result.scalars().unique().all()]

    async def get_meal(self, catalog_meal_id: str) -> CatalogMeal | None:
        result = await self._session.execute(
            select(MealCatalogORM)
            .where(MealCatalogORM.id == catalog_meal_id)
            .where(MealCatalogORM.is_active.is_(True))
            .options(_catalog_meal_load_options())
        )
        row = result.scalar_one_or_none()
        return _meal_to_domain(row) if row else None

    async def get_active_release(self):
        """Temporary compatibility: the four-table catalog has no release row."""

        return None


def _meal_type_column(meal_type: str):
    if meal_type == "breakfast":
        return MealCatalogORM.breakfast_eligible
    if meal_type == "lunch":
        return MealCatalogORM.lunch_eligible
    if meal_type == "dinner":
        return MealCatalogORM.dinner_eligible
    if meal_type == "snack":
        return MealCatalogORM.snack_eligible
    raise ValueError(f"unsupported meal_type: {meal_type}")


def _catalog_meal_load_options():
    return (
        selectinload(MealCatalogORM.ingredients)
        .selectinload(MealCatalogIngredientORM.food_reference)
        .selectinload(FoodReferenceModel.serving_size_rows)
    )


def _meal_to_domain(row: MealCatalogORM) -> CatalogMeal:
    nutrition = _nutrition_totals(row)
    return CatalogMeal(
        id=cast(str, row.id),
        catalog_key=cast(str, row.catalog_key),
        content_hash=cast(str, row.content_hash),
        name=cast(str, row.name),
        cuisine=cast(str, row.cuisine),
        description=cast(str | None, row.description),
        image_url=cast(str | None, row.image_url),
        protein_g=_decimal(nutrition.protein),
        carbs_g=_decimal(nutrition.carbs),
        fat_g=_decimal(nutrition.fat),
        fiber_g=_decimal(nutrition.fiber),
        sugar_g=_decimal(nutrition.sugar),
        meal_types=_meal_types(row),
        ingredients=tuple(_ingredient_to_domain(item) for item in row.ingredients),
        is_active=cast(bool, row.is_active),
    )


def _nutrition_totals(row: MealCatalogORM) -> ResolvedIngredientQuantity:
    totals = {
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
        "fiber": 0.0,
        "sugar": 0.0,
        "calories": 0.0,
    }
    for ingredient in row.ingredients:
        resolved = _resolve_ingredient_nutrition(ingredient)
        totals["protein"] += resolved.protein
        totals["carbs"] += resolved.carbs
        totals["fat"] += resolved.fat
        totals["fiber"] += resolved.fiber
        totals["sugar"] += resolved.sugar
        totals["calories"] += resolved.calories
    return ResolvedIngredientQuantity(
        food_reference_id=None,
        display_name=cast(str, row.name),
        quantity=1,
        unit="meal",
        grams=0,
        protein=totals["protein"],
        carbs=totals["carbs"],
        fat=totals["fat"],
        fiber=totals["fiber"],
        sugar=totals["sugar"],
        calories=totals["calories"],
    )


def _resolve_ingredient_nutrition(
    row: MealCatalogIngredientORM,
) -> ResolvedIngredientQuantity:
    reference = food_reference_model_to_nutrition_projection(row.food_reference)
    return _CATALOG_CONVERTER.resolve(
        reference=reference,
        quantity=float(row.quantity),
        unit=cast(str, row.unit),
        display_name=cast(str, row.display_name),
    )


def _ingredient_to_domain(row: MealCatalogIngredientORM) -> CatalogMealIngredient:
    return CatalogMealIngredient(
        food_reference_id=cast(int, row.food_reference_id),
        display_name=cast(str, row.display_name),
        quantity=_decimal(row.quantity),
        unit=cast(str, row.unit),
    )


def _meal_types(row: MealCatalogORM) -> tuple[str, ...]:
    values: list[str] = []
    if row.breakfast_eligible:
        values.append("breakfast")
    if row.lunch_eligible:
        values.append("lunch")
    if row.dinner_eligible:
        values.append("dinner")
    if row.snack_eligible:
        values.append("snack")
    return tuple(values)


def _decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value or "0"))
