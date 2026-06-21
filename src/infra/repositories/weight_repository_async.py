"""Async weight entry repository."""

import logging

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.weight import WeightEntry
from src.infra.database.models.weight_entry import WeightEntryORM
from src.infra.mappers.weight_entry_mapper import (
    weight_entry_domain_to_orm,
    weight_entry_orm_to_domain,
)

logger = logging.getLogger(__name__)


class AsyncWeightRepository:
    """Async weight entry repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, entry: WeightEntry) -> WeightEntry:
        """Add a weight entry. Returns the entry with created_at populated."""
        db = weight_entry_domain_to_orm(entry)
        self.session.add(db)
        await self.session.flush()
        await self.session.refresh(db)
        return weight_entry_orm_to_domain(db)

    async def find_by_id(self, user_id: str, entry_id: str) -> WeightEntry | None:
        """Find entry by ID for a specific user."""
        result = await self.session.execute(
            select(WeightEntryORM).where(
                WeightEntryORM.id == entry_id,
                WeightEntryORM.user_id == user_id,
            )
        )
        db = result.scalars().first()
        return weight_entry_orm_to_domain(db) if db else None

    async def find_by_user(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> list[WeightEntry]:
        """Get weight entries for a user, ordered by recorded_at desc."""
        result = await self.session.execute(
            select(WeightEntryORM)
            .where(WeightEntryORM.user_id == user_id)
            .order_by(WeightEntryORM.recorded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [weight_entry_orm_to_domain(r) for r in result.scalars().all()]

    async def find_by_recorded_range(
        self,
        user_id: str,
        start_utc,
        end_utc,
    ) -> list[WeightEntry]:
        """Get weight entries in a strict recorded_at UTC range."""
        result = await self.session.execute(
            select(WeightEntryORM)
            .where(
                WeightEntryORM.user_id == user_id,
                WeightEntryORM.recorded_at >= start_utc,
                WeightEntryORM.recorded_at < end_utc,
            )
            .order_by(WeightEntryORM.recorded_at.asc())
        )
        return [weight_entry_orm_to_domain(r) for r in result.scalars().all()]

    async def delete(self, user_id: str, entry_id: str) -> bool:
        """Delete entry by ID. Returns True if deleted."""
        result = await self.session.execute(
            delete(WeightEntryORM).where(
                WeightEntryORM.id == entry_id,
                WeightEntryORM.user_id == user_id,
            )
        )
        return result.rowcount > 0

    async def bulk_upsert(self, user_id: str, entries: list[WeightEntry]) -> int:
        """Bulk upsert entries. Returns count of affected rows."""
        if not entries:
            return 0

        values = [
            {
                "id": e.id,
                "user_id": user_id,
                "weight_kg": e.weight_kg,
                "recorded_at": e.recorded_at,
            }
            for e in entries
        ]

        stmt = insert(WeightEntryORM).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_user_recorded_at",
            set_={
                "weight_kg": stmt.excluded.weight_kg,
            },
        )

        result = await self.session.execute(stmt)
        return result.rowcount
