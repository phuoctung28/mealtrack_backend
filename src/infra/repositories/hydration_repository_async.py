"""Async hydration entry repository backed by asyncpg + AsyncSession."""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.hydration.hydration_entry import HydrationEntry, DrinkType
from src.domain.utils.timezone_utils import get_zone_info
from src.infra.database.models.hydration.hydration_entry_orm import HydrationEntryORM
from src.infra.database.models.user.user import User

logger = logging.getLogger(__name__)


def _orm_to_domain(row: HydrationEntryORM) -> HydrationEntry:
    return HydrationEntry(
        hydration_entry_id=row.id,
        user_id=row.user_id,
        drink_type=DrinkType(row.drink_type),
        volume_ml=row.volume_ml,
        logged_at=row.logged_at,
        created_at=row.created_at,
    )


class AsyncHydrationRepository:
    """Async hydration entry repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, entry: HydrationEntry) -> HydrationEntry:
        """Insert a new hydration entry. Returns the persisted entry."""
        row = HydrationEntryORM(
            id=entry.hydration_entry_id,
            user_id=entry.user_id,
            drink_type=entry.drink_type.value,
            volume_ml=entry.volume_ml,
            logged_at=entry.logged_at,
            created_at=entry.created_at,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return _orm_to_domain(row)

    async def find_by_id(self, entry_id: str) -> Optional[HydrationEntry]:
        """Find a hydration entry by primary key."""
        result = await self.session.execute(
            select(HydrationEntryORM).where(HydrationEntryORM.id == entry_id)
        )
        row = result.scalars().first()
        return _orm_to_domain(row) if row else None

    async def find_for_user_date(
        self,
        user_id: str,
        target_date: date,
        user_timezone: str = "UTC",
    ) -> List[HydrationEntry]:
        """Return all hydration entries for a user on a given local date.

        Converts the local date to UTC boundaries for correct filtering
        against the UTC-stored logged_at column.
        """
        tz = get_zone_info(user_timezone)
        start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
        end_dt = start_dt + timedelta(days=1)

        result = await self.session.execute(
            select(HydrationEntryORM)
            .where(
                HydrationEntryORM.user_id == user_id,
                HydrationEntryORM.logged_at >= start_dt,
                HydrationEntryORM.logged_at < end_dt,
            )
            .order_by(HydrationEntryORM.logged_at.asc())
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def delete(self, entry_id: str, user_id: str) -> bool:
        """Hard-delete a hydration entry. Returns True if a row was deleted.

        Filters by both entry_id and user_id so cross-user deletes are rejected
        at the DB level (no rows matched = caller raises 403).
        """
        result = await self.session.execute(
            delete(HydrationEntryORM).where(
                HydrationEntryORM.id == entry_id,
                HydrationEntryORM.user_id == user_id,
            )
        )
        return result.rowcount > 0

    async def get_user_hydration_goal(self, user_id: str) -> int:
        """Fetch the user's current hydration_goal_ml from the users table."""
        result = await self.session.execute(
            select(User.hydration_goal_ml).where(User.id == user_id)
        )
        goal = result.scalars().first()
        return int(goal) if goal is not None else 2000

    async def update_user_hydration_goal(self, user_id: str, goal_ml: int) -> int:
        """Update users.hydration_goal_ml. Returns the new value."""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(hydration_goal_ml=goal_ml)
        )
        return goal_ml
