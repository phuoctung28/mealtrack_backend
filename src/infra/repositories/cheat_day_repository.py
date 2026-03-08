"""Repository for cheat day persistence."""
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.model.cheat_day import CheatDay
from src.infra.database.models.cheat_day import CheatDay as DBCheatDay


class CheatDayRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, cheat_day: CheatDay) -> None:
        db_cheat_day = DBCheatDay.from_domain(cheat_day)
        self.session.add(db_cheat_day)

    def find_by_user_and_date(self, user_id: str, target_date: date) -> Optional[CheatDay]:
        db = self.session.query(DBCheatDay).filter(
            DBCheatDay.user_id == user_id,
            DBCheatDay.date == target_date,
        ).first()
        return db.to_domain() if db else None

    def find_by_user_and_date_range(self, user_id: str, start: date, end: date) -> List[CheatDay]:
        rows = self.session.query(DBCheatDay).filter(
            DBCheatDay.user_id == user_id,
            DBCheatDay.date >= start,
            DBCheatDay.date <= end,
        ).order_by(DBCheatDay.date).all()
        return [r.to_domain() for r in rows]

    def delete(self, cheat_day_id: str):
        self.session.query(DBCheatDay).filter(
            DBCheatDay.id == cheat_day_id,
        ).delete()
