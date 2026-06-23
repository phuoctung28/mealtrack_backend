"""Async movement repository."""

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.movement import MovementEntry
from src.infra.database.models.movement_entry import MovementEntryORM
from src.infra.mappers.movement_entry_mapper import (
    movement_entry_domain_to_orm,
    movement_entry_orm_to_domain,
)


class AsyncMovementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, entry: MovementEntry) -> MovementEntry:
        db = movement_entry_domain_to_orm(entry)
        self.session.add(db)
        await self.session.flush()
        await self.session.refresh(db)
        return movement_entry_orm_to_domain(db)

    async def find_by_id(self, user_id: str, entry_id: str) -> MovementEntry | None:
        result = await self.session.execute(
            select(MovementEntryORM).where(
                MovementEntryORM.id == entry_id,
                MovementEntryORM.user_id == user_id,
            )
        )
        db = result.scalars().first()
        return movement_entry_orm_to_domain(db) if db else None

    async def find_by_user_and_logged_range(
        self,
        user_id: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[MovementEntry]:
        result = await self.session.execute(
            select(MovementEntryORM)
            .where(
                MovementEntryORM.user_id == user_id,
                MovementEntryORM.logged_at >= start_utc,
                MovementEntryORM.logged_at < end_utc,
            )
            .order_by(
                MovementEntryORM.logged_at.desc(), MovementEntryORM.created_at.desc()
            )
        )
        return [movement_entry_orm_to_domain(row) for row in result.scalars().all()]

    async def sum_included_kcal_for_range(
        self,
        user_id: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(MovementEntryORM.kcal_burned), 0.0)).where(
                MovementEntryORM.user_id == user_id,
                MovementEntryORM.include_in_balance.is_(True),
                MovementEntryORM.logged_at >= start_utc,
                MovementEntryORM.logged_at < end_utc,
            )
        )
        return float(result.scalar_one() or 0.0)

    async def fetch_included_kcal_for_range(
        self,
        user_id: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[tuple[datetime, float]]:
        """Return (logged_at, kcal_burned) for all include_in_balance entries.

        Single query covering the full range — callers bucket by local date.
        """
        result = await self.session.execute(
            select(MovementEntryORM.logged_at, MovementEntryORM.kcal_burned).where(
                MovementEntryORM.user_id == user_id,
                MovementEntryORM.include_in_balance.is_(True),
                MovementEntryORM.logged_at >= start_utc,
                MovementEntryORM.logged_at < end_utc,
            )
        )
        return [(row.logged_at, float(row.kcal_burned)) for row in result.all()]

    async def fetch_journey_progress_movements(
        self,
        user_id: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[dict]:
        result = await self.session.execute(
            select(MovementEntryORM.logged_at, MovementEntryORM.activity_name)
            .where(
                MovementEntryORM.user_id == user_id,
                MovementEntryORM.logged_at >= start_utc,
                MovementEntryORM.logged_at < end_utc,
            )
            .order_by(MovementEntryORM.logged_at.asc())
        )
        return [
            {
                "logged_at": logged_at,
                "label": activity_name or "Activity",
            }
            for logged_at, activity_name in result.all()
        ]

    async def update(
        self,
        user_id: str,
        entry_id: str,
        duration_min: int,
        kcal_burned: float,
        intensity: str,
        include_in_balance: bool,
    ) -> MovementEntry | None:
        result = await self.session.execute(
            select(MovementEntryORM).where(
                MovementEntryORM.id == entry_id,
                MovementEntryORM.user_id == user_id,
            )
        )
        row = result.scalars().first()
        if row is None:
            return None
        row.duration_min = duration_min
        row.kcal_burned = kcal_burned
        row.intensity = intensity
        row.include_in_balance = include_in_balance
        await self.session.flush()
        await self.session.refresh(row)
        return movement_entry_orm_to_domain(row)

    async def delete(self, user_id: str, entry_id: str) -> bool:
        result = await self.session.execute(
            delete(MovementEntryORM).where(
                MovementEntryORM.id == entry_id,
                MovementEntryORM.user_id == user_id,
            )
        )
        return result.rowcount > 0
