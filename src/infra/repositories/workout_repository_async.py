"""Async workout log repository backed by asyncpg + AsyncSession."""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.workout.workout_log import WorkoutLog, WorkoutType, Intensity
from src.domain.utils.timezone_utils import get_zone_info
from src.infra.database.models.workout.workout_log_orm import WorkoutLogORM

logger = logging.getLogger(__name__)


def _orm_to_domain(row: WorkoutLogORM) -> WorkoutLog:
    return WorkoutLog(
        workout_log_id=row.id,
        user_id=row.user_id,
        workout_type=WorkoutType(row.workout_type),
        intensity=Intensity(row.intensity),
        duration_minutes=row.duration_minutes,
        logged_at=row.logged_at,
        met_value=float(row.met_value),
        weight_kg_snapshot=float(row.weight_kg_snapshot) if row.weight_kg_snapshot is not None else None,
        estimated_burn_kcal=float(row.estimated_burn_kcal) if row.estimated_burn_kcal is not None else None,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class AsyncWorkoutRepository:
    """Async workout log repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, log: WorkoutLog) -> WorkoutLog:
        """Insert a new workout log row. Returns the persisted entry."""
        row = WorkoutLogORM(
            id=log.workout_log_id,
            user_id=log.user_id,
            workout_type=log.workout_type.value,
            intensity=log.intensity.value,
            duration_minutes=log.duration_minutes,
            met_value=log.met_value,
            weight_kg_snapshot=log.weight_kg_snapshot,
            estimated_burn_kcal=log.estimated_burn_kcal,
            logged_at=log.logged_at,
            notes=log.notes,
            created_at=log.created_at,
            updated_at=log.updated_at,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return _orm_to_domain(row)

    async def find_by_id(self, log_id: str) -> Optional[WorkoutLog]:
        """Find a workout log by primary key."""
        result = await self.session.execute(
            select(WorkoutLogORM).where(WorkoutLogORM.id == log_id)
        )
        row = result.scalars().first()
        return _orm_to_domain(row) if row else None

    async def find_for_user_date(
        self,
        user_id: str,
        target_date: date,
        user_timezone: str = "UTC",
    ) -> List[WorkoutLog]:
        """Return all workout logs for a user on a given local date.

        Converts the local date to UTC boundaries for correct filtering
        against the UTC-stored logged_at column.
        """
        tz = get_zone_info(user_timezone)
        start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
        end_dt = start_dt + timedelta(days=1)

        result = await self.session.execute(
            select(WorkoutLogORM)
            .where(
                WorkoutLogORM.user_id == user_id,
                WorkoutLogORM.logged_at >= start_dt,
                WorkoutLogORM.logged_at < end_dt,
            )
            .order_by(WorkoutLogORM.logged_at.asc())
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def delete(self, log_id: str, user_id: str) -> bool:
        """Hard-delete a workout log. Returns True if a row was deleted.

        Filters by both log_id and user_id so cross-user deletes are rejected
        at the DB level (no rows matched = caller raises 403).
        """
        result = await self.session.execute(
            delete(WorkoutLogORM).where(
                WorkoutLogORM.id == log_id,
                WorkoutLogORM.user_id == user_id,
            )
        )
        return result.rowcount > 0
