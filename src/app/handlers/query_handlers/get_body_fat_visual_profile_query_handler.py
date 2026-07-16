"""Read visual body-fat profile history independently from measured metrics."""

from typing import Any

from sqlalchemy import select

from src.app.events.base import EventHandler, handles
from src.app.queries.user.get_body_fat_visual_profile_query import (
    GetBodyFatVisualProfileQuery,
)
from src.infra.database.models.user.body_fat_visual_profile import BodyFatVisualProfile
from src.infra.database.uow_async import AsyncUnitOfWork


@handles(GetBodyFatVisualProfileQuery)
class GetBodyFatVisualProfileQueryHandler(
    EventHandler[GetBodyFatVisualProfileQuery, dict[str, Any] | None]
):
    """Return immutable selection history when a selection exists."""

    async def handle(
        self, query: GetBodyFatVisualProfileQuery
    ) -> dict[str, Any] | None:
        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                select(BodyFatVisualProfile)
                .where(BodyFatVisualProfile.user_id == query.user_id)
                .order_by(
                    BodyFatVisualProfile.updated_at.asc(),
                    BodyFatVisualProfile.id.asc(),
                )
            )
            history = [self._serialize(record) for record in result.scalars().all()]

        if not history:
            return None

        latest = history[-1]
        return {
            "schema_version": latest["schema_version"],
            "range_catalog_version": latest["range_catalog_version"],
            "sex_at_selection": latest["sex_at_selection"],
            "current_range_id": latest["current_range_id"],
            "target_range_id": latest["target_range_id"],
            "updated_at": latest["updated_at"],
            "history": history,
        }

    @staticmethod
    def _serialize(record: BodyFatVisualProfile) -> dict[str, Any]:
        return {
            "schema_version": record.schema_version,
            "range_catalog_version": record.range_catalog_version,
            "sex_at_selection": record.sex_at_selection,
            "current_range_id": record.current_range_id,
            "target_range_id": record.target_range_id,
            "updated_at": record.updated_at,
        }
