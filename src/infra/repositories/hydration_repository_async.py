"""Async hydration log repository."""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.hydration.hydration_entry import HydrationEntry
from src.domain.ports.hydration_repository_port import HydrationRepositoryPort
from src.domain.utils.timezone_utils import get_zone_info
from src.infra.database.models.hydration.hydration_log import HydrationLogORM
from src.infra.mappers.hydration_mapper import (
    hydration_entry_orm_to_domain,
    hydration_entry_domain_to_orm,
)

logger = logging.getLogger(__name__)


class AsyncHydrationRepository(HydrationRepositoryPort):
    """Async hydration log repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, entry: HydrationEntry) -> HydrationEntry:
        """Upsert a hydration entry. Returns the entry with timestamps populated."""
        result = await self.session.execute(
            select(HydrationLogORM).where(HydrationLogORM.id == entry.entry_id)
        )
        existing = result.scalars().first()

        if existing:
            existing.drink_id = entry.drink_id
            existing.volume_ml = entry.volume_ml
            existing.credited_ml = entry.credited_ml
            existing.source = (
                entry.source.value
                if hasattr(entry.source, "value")
                else entry.source
            )
            existing.meal_id = entry.meal_id
            existing.logged_at = entry.logged_at
            existing.is_deleted = entry.is_deleted
            db = existing
        else:
            db = hydration_entry_domain_to_orm(entry)
            self.session.add(db)

        await self.session.flush()
        await self.session.refresh(db)
        return hydration_entry_orm_to_domain(db)

    async def find_by_id(
        self, user_id: str, entry_id: str
    ) -> HydrationEntry | None:
        """Find a non-deleted entry by ID for a specific user."""
        result = await self.session.execute(
            select(HydrationLogORM).where(
                HydrationLogORM.id == entry_id,
                HydrationLogORM.user_id == user_id,
                HydrationLogORM.is_deleted.is_(False),
            )
        )
        db = result.scalars().first()
        return hydration_entry_orm_to_domain(db) if db else None

    async def find_by_date(
        self, user_id: str, target_date: date, user_timezone: str
    ) -> list[HydrationEntry]:
        """Return all non-deleted entries for a user on a given local date, ordered by logged_at ASC."""
        tz = get_zone_info(user_timezone)
        start_of_day = datetime(
            target_date.year, target_date.month, target_date.day, tzinfo=tz
        )
        end_of_day = start_of_day + timedelta(days=1)

        result = await self.session.execute(
            select(HydrationLogORM)
            .where(
                HydrationLogORM.user_id == user_id,
                HydrationLogORM.logged_at >= start_of_day,
                HydrationLogORM.logged_at < end_of_day,
                HydrationLogORM.is_deleted.is_(False),
            )
            .order_by(HydrationLogORM.logged_at.asc())
        )
        return [hydration_entry_orm_to_domain(row) for row in result.scalars().all()]

    async def soft_delete(self, user_id: str, entry_id: str) -> bool:
        """Set is_deleted=True for the entry. Returns True if a row was updated."""
        result = await self.session.execute(
            update(HydrationLogORM)
            .where(
                HydrationLogORM.id == entry_id,
                HydrationLogORM.user_id == user_id,
            )
            .values(is_deleted=True)
        )
        return result.rowcount > 0

    async def sum_credited_ml_by_date_range(
        self, user_id: str, start_date: date, end_date: date, user_timezone: str
    ) -> dict[date, int]:
        """Return credited_ml per local date for a date range — single query, grouped in Python."""
        tz = get_zone_info(user_timezone)
        start_utc = datetime(start_date.year, start_date.month, start_date.day, tzinfo=tz)
        end_utc = datetime(end_date.year, end_date.month, end_date.day, tzinfo=tz) + timedelta(days=1)

        result = await self.session.execute(
            select(HydrationLogORM.logged_at, HydrationLogORM.credited_ml).where(
                HydrationLogORM.user_id == user_id,
                HydrationLogORM.logged_at >= start_utc,
                HydrationLogORM.logged_at < end_utc,
                HydrationLogORM.is_deleted.is_(False),
            )
        )
        totals: dict[date, int] = {}
        for logged_at, credited_ml in result.all():
            local_date = logged_at.astimezone(tz).date()
            totals[local_date] = totals.get(local_date, 0) + (credited_ml or 0)
        return totals

    async def sum_credited_ml_for_date(
        self, user_id: str, target_date: date, user_timezone: str
    ) -> int:
        """Sum credited_ml for all non-deleted entries on a given local date."""
        tz = get_zone_info(user_timezone)
        start_of_day = datetime(
            target_date.year, target_date.month, target_date.day, tzinfo=tz
        )
        end_of_day = start_of_day + timedelta(days=1)

        result = await self.session.execute(
            select(func.sum(HydrationLogORM.credited_ml)).where(
                HydrationLogORM.user_id == user_id,
                HydrationLogORM.logged_at >= start_of_day,
                HydrationLogORM.logged_at < end_of_day,
                HydrationLogORM.is_deleted.is_(False),
            )
        )
        total = result.scalar()
        return total if total is not None else 0
