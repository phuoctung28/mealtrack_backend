"""Async cheat day repository."""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database.models.cheat_day.cheat_day import CheatDayORM


class AsyncCheatDayRepository:
    """Async cheat day repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        cheat_day_id: str,
        user_id: str,
        target_date: date,
        marked_at: datetime,
    ) -> None:
        cheat_day = CheatDayORM(
            id=cheat_day_id,
            user_id=user_id,
            date=target_date,
            marked_at=marked_at,
        )
        self.session.add(cheat_day)
        await self.session.flush()

    async def find_by_user_and_date(
        self, user_id: str, target_date: date
    ) -> Optional[CheatDayORM]:
        result = await self.session.execute(
            select(CheatDayORM).where(
                CheatDayORM.user_id == user_id,
                CheatDayORM.date == target_date,
            )
        )
        return result.scalars().first()

    async def find_by_user_and_date_range(
        self, user_id: str, start: date, end: date
    ) -> List[CheatDayORM]:
        result = await self.session.execute(
            select(CheatDayORM)
            .where(
                CheatDayORM.user_id == user_id,
                CheatDayORM.date >= start,
                CheatDayORM.date <= end,
            )
            .order_by(CheatDayORM.date)
        )
        return list(result.scalars().all())

    async def delete(self, cheat_day_id: str) -> None:
        await self.session.execute(
            delete(CheatDayORM).where(CheatDayORM.id == cheat_day_id)
        )
