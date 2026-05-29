from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infra.database.models.crave.crave_seen_model import CraveSeen


class CraveSeenRepository:
    def __init__(self, session: Session):
        self._session = session

    def mark_seen(self, user_id: str, meal_ids: list[str]) -> None:
        for meal_id in meal_ids:
            row = self._session.get(
                CraveSeen, {"user_id": user_id, "catalog_meal_id": meal_id}
            )
            if row is None:
                self._session.add(
                    CraveSeen(
                        user_id=user_id,
                        catalog_meal_id=meal_id,
                        seen_count=1,
                    )
                )
                continue
            seen_record = cast(Any, row)
            seen_record.seen_count = (row.seen_count or 0) + 1
            seen_record.last_seen_at = datetime.now(UTC)

    def seen_ids(self, user_id: str) -> list[str]:
        rows = self._session.execute(
            select(CraveSeen.catalog_meal_id).where(CraveSeen.user_id == user_id)
        )
        return [row[0] for row in rows]
