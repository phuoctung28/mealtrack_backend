"""Async repository for append-only visual body-fat profile selections."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.user.body_fat_visual import BodyFatVisualProfileSelection
from src.domain.ports.body_fat_visual_profile_repository_port import (
    BodyFatVisualProfileRepositoryPort,
)
from src.infra.database.models.user.body_fat_visual_profile import (
    BodyFatVisualProfile,
)


class AsyncBodyFatVisualProfileRepository(BodyFatVisualProfileRepositoryPort):
    """Persist and read visual selection history without owning commits."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def append(self, selection: BodyFatVisualProfileSelection) -> None:
        self.session.add(
            BodyFatVisualProfile(
                id=str(selection.id),
                user_id=selection.user_id,
                schema_version=selection.schema_version,
                range_catalog_version=selection.range_catalog_version,
                sex_at_selection=selection.sex_at_selection,
                start_range_id=selection.start_range_id,
                current_range_id=selection.current_range_id,
                target_range_id=selection.target_range_id,
            )
        )

    async def find_history_by_user(
        self, user_id: str
    ) -> list[BodyFatVisualProfileSelection]:
        result = await self.session.execute(
            select(BodyFatVisualProfile)
            .where(BodyFatVisualProfile.user_id == user_id)
            .order_by(
                BodyFatVisualProfile.updated_at.asc(),
                BodyFatVisualProfile.id.asc(),
            )
        )
        return [self._to_domain(record) for record in result.scalars().all()]

    @staticmethod
    def _to_domain(record: BodyFatVisualProfile) -> BodyFatVisualProfileSelection:
        return BodyFatVisualProfileSelection(
            id=UUID(record.id),
            user_id=record.user_id,
            schema_version=record.schema_version,
            range_catalog_version=record.range_catalog_version,
            sex_at_selection=record.sex_at_selection,
            start_range_id=record.start_range_id,
            current_range_id=record.current_range_id,
            target_range_id=record.target_range_id,
            updated_at=record.updated_at,
        )
