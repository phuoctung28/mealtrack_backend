"""Async meal repository backed by asyncpg + AsyncSession."""

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, noload, selectinload

from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_projection import MealProjection
from src.domain.model.nutrition import Nutrition
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.utils.timezone_utils import get_zone_info, utc_now
from src.infra.database.models.enums import MealStatusEnum
from src.infra.database.models.meal.food_item_translation_model import (
    FoodItemTranslationORM,
)
from src.infra.database.models.meal.meal import MealORM
from src.infra.database.models.meal.meal_image import MealImageORM
from src.infra.database.models.meal.meal_translation_model import MealTranslationORM
from src.infra.database.models.nutrition.food_item import FoodItemORM
from src.infra.database.models.nutrition.nutrition import NutritionORM
from src.infra.mappers import MealStatusMapper
from src.infra.mappers.meal_mapper import (
    _instruction_steps_to_orm,
    food_item_domain_to_orm,
    meal_domain_to_orm,
    meal_image_domain_to_orm,
    meal_orm_to_domain,
    meal_orm_to_domain_if_hydratable,
    nutrition_domain_to_orm,
)

logger = logging.getLogger(__name__)


_PROJECTION_OPTS: dict = {
    MealProjection.MACROS_ONLY: (
        noload(MealORM.image),
        selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items),
        selectinload(MealORM.instruction_steps),
    ),
    MealProjection.FULL: (
        joinedload(MealORM.image),
        selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items),
        selectinload(MealORM.instruction_steps),
    ),
    MealProjection.FULL_WITH_TRANSLATIONS: (
        joinedload(MealORM.image),
        selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items),
        selectinload(MealORM.instruction_steps),
        joinedload(MealORM.translations),
    ),
}


def _domain_hydratable_active_meal_filter():
    return and_(
        MealORM.status != MealStatusEnum.INACTIVE,
        or_(
            MealORM.status != MealStatusEnum.READY,
            and_(MealORM.ready_at.is_not(None), MealORM.nutrition.has()),
        ),
    )


def _map_domain_hydratable_meals(db_meals: list[MealORM]) -> list[Meal]:
    meals: list[Meal] = []
    for db_meal in db_meals:
        meal = meal_orm_to_domain_if_hydratable(db_meal)
        if meal is not None:
            meals.append(meal)
    return meals


class AsyncMealRepository(MealRepositoryPort):
    """Async SQLAlchemy meal repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, meal: Meal) -> Meal:
        result = await self.session.execute(
            select(MealORM)
            .options(
                selectinload(MealORM.nutrition).selectinload(NutritionORM.food_items),
                selectinload(MealORM.instruction_steps),
            )
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
            existing_meal.food_label_metadata = meal.food_label_metadata
            existing_meal.updated_at = meal.updated_at or utc_now()
            existing_meal.last_edited_at = meal.last_edited_at
            existing_meal.edit_count = meal.edit_count
            existing_meal.is_manually_edited = meal.is_manually_edited
            existing_meal.emoji = meal.emoji
            existing_meal.description = meal.description
            existing_meal.instructions = meal.instructions
            existing_meal.prep_time_min = meal.prep_time_min
            existing_meal.cook_time_min = meal.cook_time_min
            existing_meal.cuisine_type = meal.cuisine_type
            existing_meal.origin_country = meal.origin_country
            existing_meal.instruction_steps = _instruction_steps_to_orm(
                meal.instructions
            )

            # Update image URL if changed (parallel upload sets URL after initial save)
            if meal.image and meal.image.url:
                img_result = await self.session.execute(
                    select(MealImageORM).where(
                        MealImageORM.image_id == meal.image.image_id
                    )
                )
                existing_image = img_result.scalars().first()
                if existing_image and existing_image.url != meal.image.url:
                    existing_image.url = meal.image.url

            if meal.nutrition:
                if not existing_meal.nutrition:
                    db_nutrition = nutrition_domain_to_orm(
                        meal.nutrition, meal_id=meal.meal_id
                    )
                    existing_meal.nutrition = db_nutrition
                else:
                    await self._update_nutrition(
                        existing_meal.nutrition, meal.nutrition
                    )

            await self.session.flush()
            # Re-fetch with eager loading so mapper can access nutrition/food_items
            result2 = await self.session.execute(
                select(MealORM)
                .options(
                    selectinload(MealORM.nutrition).selectinload(
                        NutritionORM.food_items
                    ),
                    selectinload(MealORM.instruction_steps),
                )
                .where(MealORM.meal_id == meal.meal_id)
            )
            existing_meal = result2.scalars().first()
            return meal_orm_to_domain(existing_meal)
        else:
            db_meal = meal_domain_to_orm(meal)
            if meal.image:
                img_result = await self.session.execute(
                    select(MealImageORM).where(
                        MealImageORM.image_id == meal.image.image_id
                    )
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
                .options(
                    selectinload(MealORM.nutrition).selectinload(
                        NutritionORM.food_items
                    ),
                    selectinload(MealORM.instruction_steps),
                )
                .where(MealORM.meal_id == db_meal.meal_id)
            )
            db_meal = result2.scalars().first()
            return meal_orm_to_domain(db_meal)

    async def find_by_id(
        self, meal_id: str, projection: MealProjection = MealProjection.FULL
    ) -> Meal | None:
        result = await self.session.execute(
            select(MealORM)
            .options(*_PROJECTION_OPTS[projection])
            .where(MealORM.meal_id == meal_id)
        )
        # .unique() required for joinedload to properly consolidate joined rows
        db_meal = result.unique().scalars().first()
        return meal_orm_to_domain(db_meal) if db_meal else None

    async def find_by_status(self, status: MealStatus, limit: int = 10) -> list[Meal]:
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
                .where(
                    FoodItemTranslationORM.meal_translation_id.in_(meal_translation_ids)
                )
                .values(is_deleted=True)
            )
        await self.session.execute(
            delete(NutritionORM).where(NutritionORM.meal_id == meal_id)
        )
        await self.session.execute(delete(MealORM).where(MealORM.meal_id == meal_id))

    async def find_by_date(
        self,
        date_obj: date,
        user_id: str = None,
        limit: int = 50,
        user_timezone: str | None = None,
        projection: MealProjection = MealProjection.FULL,
        meal_type: str | None = None,
    ) -> list[Meal]:
        tz = get_zone_info(user_timezone) if user_timezone else UTC
        start_dt = datetime.combine(
            date_obj, datetime.min.time(), tzinfo=tz
        ).astimezone(UTC)
        end_dt = start_dt + timedelta(days=1)

        stmt = (
            select(MealORM)
            .options(*_PROJECTION_OPTS[projection])
            .where(
                MealORM.created_at >= start_dt,
                MealORM.created_at < end_dt,
                _domain_hydratable_active_meal_filter(),
            )
        )
        if user_id:
            stmt = stmt.where(MealORM.user_id == user_id)
        if meal_type is not None:
            stmt = stmt.where(MealORM.meal_type == meal_type)
        stmt = stmt.order_by(MealORM.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return _map_domain_hydratable_meals(result.scalars().all())

    async def find_activities_by_date(
        self,
        date_obj: date,
        user_id: str,
        user_timezone: str | None = None,
    ) -> list[Meal]:
        """Return all meals (food + hydration) for a date, sorted by timestamp DESC."""
        tz = get_zone_info(user_timezone) if user_timezone else UTC
        start_dt = datetime.combine(
            date_obj, datetime.min.time(), tzinfo=tz
        ).astimezone(UTC)
        end_dt = start_dt + timedelta(days=1)

        result = await self.session.execute(
            select(MealORM)
            .options(*_PROJECTION_OPTS[MealProjection.FULL_WITH_TRANSLATIONS])
            .where(
                MealORM.user_id == user_id,
                MealORM.created_at >= start_dt,
                MealORM.created_at < end_dt,
                MealORM.status.in_([MealStatusEnum.READY, MealStatusEnum.ENRICHING]),
                _domain_hydratable_active_meal_filter(),
            )
            .order_by(MealORM.created_at.desc())
        )
        return [meal_orm_to_domain(m) for m in result.unique().scalars().all()]

    async def sum_hydration_ml_for_date(
        self,
        date_obj: date,
        user_id: str,
        user_timezone: str | None = None,
    ) -> int:
        """Return total hydration ml logged for a single date."""
        tz = get_zone_info(user_timezone) if user_timezone else UTC
        start_dt = datetime.combine(
            date_obj, datetime.min.time(), tzinfo=tz
        ).astimezone(UTC)
        end_dt = start_dt + timedelta(days=1)

        result = await self.session.execute(
            select(func.coalesce(func.sum(MealORM.quantity), 0)).where(
                MealORM.user_id == user_id,
                MealORM.meal_type == "hydration",
                MealORM.created_at >= start_dt,
                MealORM.created_at < end_dt,
                _domain_hydratable_active_meal_filter(),
            )
        )
        return result.scalar_one()

    async def sum_hydration_ml_by_date_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        user_timezone: str | None = None,
    ) -> dict[date, int]:
        """Return per-date hydration totals (ml) for a date range."""
        tz = get_zone_info(user_timezone) if user_timezone else UTC
        start_dt = datetime.combine(
            start_date, datetime.min.time(), tzinfo=tz
        ).astimezone(UTC)
        end_dt = (
            datetime.combine(end_date, datetime.min.time(), tzinfo=tz)
            + timedelta(days=1)
        ).astimezone(UTC)

        if user_timezone and user_timezone != "UTC":
            date_expr = func.date(func.timezone(user_timezone, MealORM.created_at))
        else:
            date_expr = func.date(MealORM.created_at)

        result = await self.session.execute(
            select(date_expr, func.coalesce(func.sum(MealORM.quantity), 0))
            .where(
                MealORM.user_id == user_id,
                MealORM.meal_type == "hydration",
                MealORM.created_at >= start_dt,
                MealORM.created_at < end_dt,
                _domain_hydratable_active_meal_filter(),
            )
            .group_by(date_expr)
        )
        out: dict[date, int] = {}
        for day_val, total in result.all():
            if isinstance(day_val, str):
                day_val = date.fromisoformat(day_val)
            out[day_val] = int(total)
        return out

    async def find_by_date_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        limit: int = 500,
        user_timezone: str | None = None,
        projection: MealProjection = MealProjection.FULL,
    ) -> list[Meal]:
        tz = get_zone_info(user_timezone) if user_timezone else UTC
        start_dt = datetime.combine(
            start_date, datetime.min.time(), tzinfo=tz
        ).astimezone(UTC)
        end_dt = (
            datetime.combine(end_date, datetime.min.time(), tzinfo=tz)
            + timedelta(days=1)
        ).astimezone(UTC)

        result = await self.session.execute(
            select(MealORM)
            .options(*_PROJECTION_OPTS[projection])
            .where(
                MealORM.created_at >= start_dt,
                MealORM.created_at < end_dt,
                MealORM.user_id == user_id,
                _domain_hydratable_active_meal_filter(),
            )
            .order_by(MealORM.created_at.asc())
            .limit(limit)
        )
        return _map_domain_hydratable_meals(result.unique().scalars().all())

    async def get_daily_meal_counts(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        user_timezone: str | None = None,
    ) -> dict[date, int]:
        tz = get_zone_info(user_timezone) if user_timezone else UTC
        start_dt = datetime.combine(
            start_date, datetime.min.time(), tzinfo=tz
        ).astimezone(UTC)
        end_dt = (
            datetime.combine(end_date, datetime.min.time(), tzinfo=tz)
            + timedelta(days=1)
        ).astimezone(UTC)

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
                _domain_hydratable_active_meal_filter(),
            )
            .group_by(date_expr)
        )
        out: dict[date, int] = {}
        for day_val, count in result.all():
            if isinstance(day_val, str):
                day_val = date.fromisoformat(day_val)
            out[day_val] = count
        return out

    async def fetch_journey_progress_meals(
        self,
        user_id: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[dict]:
        result = await self.session.execute(
            select(
                MealORM.created_at,
                MealORM.dish_name,
                NutritionORM.protein,
                NutritionORM.carbs,
                NutritionORM.fat,
                NutritionORM.fiber,
            )
            .join(NutritionORM, NutritionORM.meal_id == MealORM.meal_id, isouter=True)
            .where(
                MealORM.user_id == user_id,
                MealORM.created_at >= start_utc,
                MealORM.created_at < end_utc,
                or_(MealORM.meal_type.is_(None), MealORM.meal_type != "hydration"),
                _domain_hydratable_active_meal_filter(),
            )
            .order_by(MealORM.created_at.asc())
        )
        rows = []
        for logged_at, label, protein, carbs, fat, fiber in result.all():
            protein = float(protein or 0.0)
            carbs = float(carbs or 0.0)
            fat = float(fat or 0.0)
            fiber = float(fiber or 0.0)
            net_carbs = max(0.0, carbs - fiber)
            rows.append(
                {
                    "logged_at": logged_at,
                    "label": label or "Meal",
                    "calories": round(
                        protein * 4 + net_carbs * 4 + fiber * 2 + fat * 9, 1
                    ),
                    "protein_g": protein,
                }
            )
        return rows

    async def get_dates_with_meals(
        self, user_id: str, user_timezone: str | None = None
    ) -> list[date]:
        # Always PostgreSQL in async path
        if user_timezone and user_timezone != "UTC":
            date_expr = func.date(func.timezone(user_timezone, MealORM.created_at))
        else:
            date_expr = func.date(MealORM.created_at)

        result = await self.session.execute(
            select(date_expr)
            .where(
                MealORM.user_id == user_id,
                _domain_hydratable_active_meal_filter(),
            )
            .distinct()
            .order_by(date_expr.desc())
        )
        out: list[date] = []
        for (day_val,) in result.all():
            if isinstance(day_val, str):
                day_val = date.fromisoformat(day_val)
            if isinstance(day_val, date):
                out.append(day_val)
        return out

    async def count_by_source(self, user_id: str, source: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(MealORM)
            .where(MealORM.user_id == user_id, MealORM.source == source)
        )
        return result.scalar_one()

    async def find_all_paginated(self, offset: int = 0, limit: int = 20) -> list[Meal]:
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

    async def _update_nutrition(
        self, db_nutrition: NutritionORM, domain_nutrition: Nutrition
    ) -> None:
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
