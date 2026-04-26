"""Repository for cheat day persistence."""

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from src.infra.database.models.cheat_day.cheat_day import CheatDayORM


class CheatDayRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, cheat_day: CheatDayORM) -> None:
        self.session.add(cheat_day)

    def find_by_user_and_date(
        self, user_id: str, target_date: date
    ) -> Optional[CheatDayORM]:
        return (
            self.session.query(CheatDayORM)
            .filter(
                CheatDayORM.user_id == user_id,
                CheatDayORM.date == target_date,
            )
            .first()
        )

    def find_by_user_and_date_range(
        self, user_id: str, start: date, end: date
    ) -> List[CheatDayORM]:
        return (
            self.session.query(CheatDayORM)
            .filter(
                CheatDayORM.user_id == user_id,
                CheatDayORM.date >= start,
                CheatDayORM.date <= end,
            )
            .order_by(CheatDayORM.date)
            .all()
        )

    def delete(self, cheat_day_id: str) -> None:
        self.session.query(CheatDayORM).filter(
            CheatDayORM.id == cheat_day_id,
        ).delete()
