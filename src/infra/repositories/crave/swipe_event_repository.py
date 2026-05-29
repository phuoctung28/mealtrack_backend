from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.infra.database.models.crave.crave_swipe_event_model import CraveSwipeEvent


class SwipeEventRepository:
    def __init__(self, session: Session):
        self._session = session

    def bulk_insert(self, rows: list[dict]) -> None:
        self._session.bulk_insert_mappings(CraveSwipeEvent.__mapper__, rows)

    def count_for_user(self, user_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(CraveSwipeEvent)
            .where(CraveSwipeEvent.user_id == user_id)
        )
        return int(self._session.execute(stmt).scalar() or 0)
