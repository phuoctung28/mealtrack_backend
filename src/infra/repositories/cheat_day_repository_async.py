"""Async cheat day repository."""
from datetime import date
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.cheat_day import CheatDay
from src.infra.database.models.cheat_day.cheat_day import CheatDayORM
from src.infra.mappers.cheat_day_mapper import cheat_day_orm_to_domain, cheat_day_domain_to_orm


class AsyncCheatDayRepository:
    """Async cheat day repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, cheat_day: CheatDay) -> None:
        db = cheat_day_domain_to_orm(cheat_day)
        self.session.add(db)

    async def find_by_user_and_date(self, user_id: str, target_date: date) -> Optional[CheatDay]:
        result = await self.session.execute(
            select(CheatDayORM)
            .where(
                CheatDayORM.user_id == user_id,
                CheatDayORM.date == target_date,
            )
        )
        db = result.scalars().first()
        return cheat_day_orm_to_domain(db) if db else None

    async def find_by_user_and_date_range(
        self, user_id: str, start: date, end: date
    ) -> List[CheatDay]:
        result = await self.session.execute(
            select(CheatDayORM)
            .where(
                CheatDayORM.user_id == user_id,
                CheatDayORM.date >= start,
                CheatDayORM.date <= end,
            )
            .order_by(CheatDayORM.date)
        )
        return [cheat_day_orm_to_domain(r) for r in result.scalars().all()]

    async def delete(self, cheat_day_id: str) -> None:
        await self.session.execute(
            delete(CheatDayORM).where(CheatDayORM.id == cheat_day_id)
        )
