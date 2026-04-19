"""Async weekly budget repository."""
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.weekly import WeeklyMacroBudget
from src.infra.database.models.weekly.weekly_macro_budget import WeeklyMacroBudgetORM
from src.infra.mappers.weekly_budget_mapper import weekly_budget_orm_to_domain


class AsyncWeeklyBudgetRepository:
    """Async repository for weekly macro budget. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_user_and_week(self, user_id: str, week_start_date: date) -> Optional[WeeklyMacroBudget]:
        result = await self.session.execute(
            select(WeeklyMacroBudgetORM)
            .where(
                WeeklyMacroBudgetORM.user_id == user_id,
                WeeklyMacroBudgetORM.week_start_date == week_start_date,
            )
        )
        db = result.scalars().first()
        return weekly_budget_orm_to_domain(db) if db else None

    async def upsert(self, budget: WeeklyMacroBudget) -> WeeklyMacroBudget:
        """INSERT ... ON CONFLICT DO UPDATE. Flushes but does not commit."""
        if not budget.weekly_budget_id:
            budget.weekly_budget_id = str(uuid.uuid4())

        values = {
            "weekly_budget_id": budget.weekly_budget_id,
            "user_id": budget.user_id,
            "week_start_date": budget.week_start_date,
            "target_calories": budget.target_calories,
            "target_protein": budget.target_protein,
            "target_carbs": budget.target_carbs,
            "target_fat": budget.target_fat,
            "consumed_calories": budget.consumed_calories,
            "consumed_protein": budget.consumed_protein,
            "consumed_carbs": budget.consumed_carbs,
            "consumed_fat": budget.consumed_fat,
        }
        stmt = pg_insert(WeeklyMacroBudgetORM).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_user_week",
            set_={
                "target_calories": stmt.excluded.target_calories,
                "target_protein": stmt.excluded.target_protein,
                "target_carbs": stmt.excluded.target_carbs,
                "target_fat": stmt.excluded.target_fat,
            },
        )
        await self.session.execute(stmt)
        await self.session.flush()

        result = await self.session.execute(
            select(WeeklyMacroBudgetORM)
            .where(
                WeeklyMacroBudgetORM.user_id == budget.user_id,
                WeeklyMacroBudgetORM.week_start_date == budget.week_start_date,
            )
        )
        db = result.scalars().first()
        if db is None:
            raise RuntimeError(
                f"upsert succeeded but re-fetch returned None "
                f"(user_id={budget.user_id}, week_start_date={budget.week_start_date})"
            )
        return weekly_budget_orm_to_domain(db)

    async def create(self, budget: WeeklyMacroBudget) -> WeeklyMacroBudget:
        """Create a new weekly budget (delegates to upsert for race-safety)."""
        return await self.upsert(budget)

    async def update(self, budget: WeeklyMacroBudget) -> WeeklyMacroBudget:
        """Update an existing weekly budget."""
        result = await self.session.execute(
            select(WeeklyMacroBudgetORM)
            .where(WeeklyMacroBudgetORM.weekly_budget_id == budget.weekly_budget_id)
        )
        db = result.scalars().first()
        if db:
            db.target_calories = budget.target_calories
            db.target_protein = budget.target_protein
            db.target_carbs = budget.target_carbs
            db.target_fat = budget.target_fat
            db.consumed_calories = budget.consumed_calories
            db.consumed_protein = budget.consumed_protein
            db.consumed_carbs = budget.consumed_carbs
            db.consumed_fat = budget.consumed_fat
            await self.session.flush()
            await self.session.refresh(db)
            return weekly_budget_orm_to_domain(db)
        return budget

    async def delete(self, weekly_budget_id: str) -> bool:
        """Delete a weekly budget."""
        result = await self.session.execute(
            select(WeeklyMacroBudgetORM)
            .where(WeeklyMacroBudgetORM.weekly_budget_id == weekly_budget_id)
        )
        db = result.scalars().first()
        if db:
            await self.session.delete(db)
            await self.session.flush()
            return True
        return False
