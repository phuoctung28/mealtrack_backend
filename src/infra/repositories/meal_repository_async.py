"""Async meal repository backed by asyncpg + AsyncSession."""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import func, update, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, noload

from src.domain.model.meal import Meal, MealStatus
from src.domain.model.nutrition import Nutrition
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.utils.timezone_utils import get_zone_info, utc_now
from src.infra.database.models.enums import MealStatusEnum
from src.infra.database.models.meal.meal import MealORM
from src.infra.database.models.meal.meal_image import MealImageORM
from src.infra.database.models.meal.food_item_translation_model import FoodItemTranslationORM
from src.infra.database.models.meal.meal_translation_model import MealTranslationORM
from src.infra.database.models.nutrition.food_item import FoodItemORM
from src.infra.database.models.nutrition.nutrition import NutritionORM
from src.infra.mappers import MealStatusMapper
from src.infra.mappers.meal_mapper import (
    meal_orm_to_domain,
    meal_domain_to_orm,
    meal_image_domain_to_orm,
    nutrition_domain_to_orm,
    food_item_domain_to_orm,
)
from src.infra.repositories.meal_repository import MealProjection

logger = logging.getLogger(__name__)




_PROJECTION_OPTS: dict = {
    MealProjection.MACROS_ONLY: (
        noload(MealORM.image),
        selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items),
    ),
    MealProjection.FULL: (
        joinedload(MealORM.image),
        selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items),
    ),
    MealProjection.FULL_WITH_TRANSLATIONS: (
        joinedload(MealORM.image),
        selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items),
        joinedload(MealORM.translations),
    ),
}


class AsyncMealRepository(MealRepositoryPort):
    """Async SQLAlchemy meal repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, meal: Meal) -> Meal:
        result = await self.session.execute(
            select(MealORM)
            .options(selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items))
            .where(MealORM.meal_id == meal.meal_id)
        )
        existing_meal = result.scalars().first()

        if existing_meal:
            existing_meal.status = MealStatusMapper.to_db(meal.status)
            existing_meal.dish_name = meal.dish_name
            existing_meal.meal_type = meal.meal_type
            existing_meal.ready_at = meal.ready_at
            existing_meal.error_message = meal.error_message
            existing_meal.raw_ai_response = meal.raw_gpt_json
            existing_meal.updated_at = meal.updated_at or utc_now()
            existing_meal.last_edited_at = meal.last_edited_at
            existing_meal.edit_count = meal.edit_count
            existing_meal.is_manually_edited = meal.is_manually_edited
            existing_meal.emoji = meal.emoji

            if meal.nutrition:
                if not existing_meal.nutrition:
                    db_nutrition = nutrition_domain_to_orm(meal.nutrition, meal_id=meal.meal_id)
                    existing_meal.nutrition = db_nutrition
                else:
                    await self._update_nutrition(existing_meal.nutrition, meal.nutrition)

            await self.session.flush()
            # Re-fetch with eager loading so mapper can access nutrition/food_items
            result2 = await self.session.execute(
                select(MealORM)
                .options(selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items))
                .where(MealORM.meal_id == meal.meal_id)
            )
            existing_meal = result2.scalars().first()
            return meal_orm_to_domain(existing_meal)
        else:
            db_meal = meal_domain_to_orm(meal)
            if meal.image:
                img_result = await self.session.execute(
                    select(MealImageORM).where(MealImageORM.image_id == meal.image.image_id)
                )
                if not img_result.scalars().first():
                    db_image = meal_image_domain_to_orm(meal.image)
                    self.session.add(db_image)
                    await self.session.flush()
                db_meal.image_id = str(meal.image.image_id)

            self.session.add(db_meal)
            await self.session.flush()
            # Re-fetch with eager loading after flush
            result2 = await self.session.execute(
                select(MealORM)
                .options(selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items))
                .where(MealORM.meal_id == db_meal.meal_id)
            )
            db_meal = result2.scalars().first()
            return meal_orm_to_domain(db_meal)

    async def find_by_id(
        self, meal_id: str, projection: MealProjection = MealProjection.FULL
    ) -> Optional[Meal]:
        result = await self.session.execute(
            select(MealORM).options(*_PROJECTION_OPTS[projection]).where(MealORM.meal_id == meal_id)
        )
        db_meal = result.scalars().first()
        return meal_orm_to_domain(db_meal) if db_meal else None

    async def find_by_status(self, status: MealStatus, limit: int = 10) -> List[Meal]:
        result = await self.session.execute(
            select(MealORM)
            .options(*_PROJECTION_OPTS[MealProjection.FULL])
            .where(MealORM.status == MealStatusMapper.to_db(status))
            .order_by(MealORM.created_at)
            .limit(limit)
        )
        return [meal_orm_to_domain(m) for m in result.scalars().all()]

    async def delete(self, meal_id: str) -> None:
        nutrition_result = await self.session.execute(
            select(NutritionORM).where(NutritionORM.meal_id == meal_id)
        )
        nutrition = nutrition_result.scalars().first()

        if nutrition:
            await self.session.execute(
                update(FoodItemORM)
                .where(FoodItemORM.nutrition_id == nutrition.id)
                .values(is_deleted=True, nutrition_id=None)
            )

        mt_result = await self.session.execute(
            select(MealTranslationORM.id).where(MealTranslationORM.meal_id == meal_id)
        )
        meal_translation_ids = [row[0] for row in mt_result.all()]

        await self.session.execute(
            update(MealTranslationORM)
            .where(MealTranslationORM.meal_id == meal_id)
            .values(is_deleted=True, meal_id=None)
        )
        if meal_translation_ids:
            await self.session.execute(
                update(FoodItemTranslationORM)
                .where(FoodItemTranslationORM.meal_translation_id.in_(meal_translation_ids))
                .values(is_deleted=True)
            )
        await self.session.execute(delete(NutritionORM).where(NutritionORM.meal_id == meal_id))
        await self.session.execute(delete(MealORM).where(MealORM.meal_id == meal_id))

    async def find_by_date(
        self,
        date_obj: date,
        user_id: str = None,
        limit: int = 50,
        user_timezone: Optional[str] = None,
        projection: MealProjection = MealProjection.FULL,
    ) -> List[Meal]:
        tz = get_zone_info(user_timezone) if user_timezone else timezone.utc
        start_dt = datetime.combine(date_obj, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
        end_dt = start_dt + timedelta(days=1)

        stmt = (
            select(MealORM)
            .options(*_PROJECTION_OPTS[projection])
            .where(
                MealORM.created_at >= start_dt,
                MealORM.created_at < end_dt,
                MealORM.status != MealStatusEnum.INACTIVE,
            )
        )
        if user_id:
            stmt = stmt.where(MealORM.user_id == user_id)
        stmt = stmt.order_by(MealORM.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return [meal_orm_to_domain(m) for m in result.scalars().all()]

    async def find_by_date_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        limit: int = 500,
        user_timezone: Optional[str] = None,
        projection: MealProjection = MealProjection.FULL,
    ) -> List[Meal]:
        tz = get_zone_info(user_timezone) if user_timezone else timezone.utc
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
        end_dt = (datetime.combine(end_date, datetime.min.time(), tzinfo=tz) + timedelta(days=1)).astimezone(timezone.utc)

        result = await self.session.execute(
            select(MealORM)
            .options(*_PROJECTION_OPTS[projection])
            .where(
                MealORM.created_at >= start_dt,
                MealORM.created_at < end_dt,
                MealORM.user_id == user_id,
                MealORM.status != MealStatusEnum.INACTIVE,
            )
            .order_by(MealORM.created_at.asc())
            .limit(limit)
        )
        return [meal_orm_to_domain(m) for m in result.scalars().all()]

    async def get_daily_meal_counts(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        user_timezone: Optional[str] = None,
    ) -> Dict[date, int]:
        tz = get_zone_info(user_timezone) if user_timezone else timezone.utc
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
        end_dt = (datetime.combine(end_date, datetime.min.time(), tzinfo=tz) + timedelta(days=1)).astimezone(timezone.utc)

        # Always PostgreSQL in async path — use timezone-aware date expression directly
        if user_timezone and user_timezone != "UTC":
            date_expr = func.date(func.timezone(user_timezone, MealORM.created_at))
        else:
            date_expr = func.date(MealORM.created_at)

        result = await self.session.execute(
            select(date_expr, func.count())
            .where(
                MealORM.user_id == user_id,
                MealORM.created_at >= start_dt,
                MealORM.created_at < end_dt,
                MealORM.status != MealStatusEnum.INACTIVE,
            )
            .group_by(date_expr)
        )
        out: Dict[date, int] = {}
        for day_val, count in result.all():
            if isinstance(day_val, str):
                day_val = date.fromisoformat(day_val)
            out[day_val] = count
        return out

    async def get_dates_with_meals(
        self, user_id: str, user_timezone: Optional[str] = None
    ) -> List[date]:
        # Always PostgreSQL in async path
        if user_timezone and user_timezone != "UTC":
            date_expr = func.date(func.timezone(user_timezone, MealORM.created_at))
        else:
            date_expr = func.date(MealORM.created_at)

        result = await self.session.execute(
            select(date_expr)
            .where(MealORM.user_id == user_id, MealORM.status != MealStatusEnum.INACTIVE)
            .distinct()
            .order_by(date_expr.desc())
        )
        out: List[date] = []
        for (day_val,) in result.all():
            if isinstance(day_val, str):
                day_val = date.fromisoformat(day_val)
            if isinstance(day_val, date):
                out.append(day_val)
        return out

    async def count_by_source(self, user_id: str, source: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(MealORM).where(
                MealORM.user_id == user_id, MealORM.source == source
            )
        )
        return result.scalar_one()

    async def find_all_paginated(self, offset: int = 0, limit: int = 20) -> List[Meal]:
        result = await self.session.execute(
            select(MealORM)
            .options(*_PROJECTION_OPTS[MealProjection.FULL])
            .order_by(MealORM.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [meal_orm_to_domain(m) for m in result.scalars().all()]

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(MealORM))
        return result.scalar_one()

    async def _update_nutrition(self, db_nutrition: NutritionORM, domain_nutrition: Nutrition) -> None:
        db_nutrition.protein = domain_nutrition.macros.protein
        db_nutrition.carbs = domain_nutrition.macros.carbs
        db_nutrition.fat = domain_nutrition.macros.fat
        db_nutrition.confidence_score = domain_nutrition.confidence_score

        # food_items pre-loaded via selectinload in save() — safe to iterate
        for item in db_nutrition.food_items:
            await self.session.delete(item)
        await self.session.flush()

        if domain_nutrition.food_items:
            for idx, item in enumerate(domain_nutrition.food_items):
                db_item = food_item_domain_to_orm(item, nutrition_id=db_nutrition.id)
                db_item.order_index = idx
                self.session.add(db_item)
