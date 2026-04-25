"""Repository for cheat day persistence."""

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.model.cheat_day import CheatDay
from src.infra.database.models.cheat_day import CheatDayORM
from src.infra.mappers.cheat_day_mapper import (
    cheat_day_orm_to_domain,
    cheat_day_domain_to_orm,
)


class CheatDayRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, cheat_day: CheatDay) -> None:
        db_cheat_day = cheat_day_domain_to_orm(cheat_day)
        self.session.add(db_cheat_day)

    def find_by_user_and_date(
        self, user_id: str, target_date: date
    ) -> Optional[CheatDay]:
        db = (
            self.session.query(CheatDayORM)
            .filter(
                CheatDayORM.user_id == user_id,
                CheatDayORM.date == target_date,
            )
            .first()
        )
        return cheat_day_orm_to_domain(db) if db else None

    def find_by_user_and_date_range(
        self, user_id: str, start: date, end: date
    ) -> List[CheatDay]:
        rows = (
            self.session.query(CheatDayORM)
            .filter(
                CheatDayORM.user_id == user_id,
                CheatDayORM.date >= start,
                CheatDayORM.date <= end,
            )
            .order_by(CheatDayORM.date)
            .all()
        )
        return [cheat_day_orm_to_domain(r) for r in rows]

    def delete(self, cheat_day_id: str):
        self.session.query(CheatDayORM).filter(
            CheatDayORM.id == cheat_day_id,
        ).delete()
