"""Handler for updating a feature flag."""

import logging
from typing import Optional

from sqlalchemy import select

from src.app.commands.feature_flag.update_feature_flag_command import (
    UpdateFeatureFlagCommand,
)
from src.app.events.base import EventHandler, handles
from src.app.queries.feature_flag.get_feature_flag_by_name_query import (
    FeatureFlagResult,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService
from src.infra.database.models.feature_flag import FeatureFlag
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


class FeatureFlagNotFoundError(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Feature flag '{name}' not found")


@handles(UpdateFeatureFlagCommand)
class UpdateFeatureFlagCommandHandler(
    EventHandler[UpdateFeatureFlagCommand, FeatureFlagResult]
):

    def __init__(
        self,
        uow: Optional[AsyncUnitOfWorkPort] = None,
        cache_service: Optional[CacheService] = None,
    ):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, command: UpdateFeatureFlagCommand) -> FeatureFlagResult:
        uow = self.uow or AsyncUnitOfWork()
        async with uow:
            result = await uow.session.execute(
                select(FeatureFlag).where(FeatureFlag.name == command.name)
            )
            flag = result.scalars().first()

            if not flag:
                raise FeatureFlagNotFoundError(command.name)

            if command.enabled is not None:
                flag.enabled = command.enabled
            if command.description is not None:
                flag.description = command.description

            flag.updated_at = utc_now()

            await uow.commit()
            await uow.session.refresh(flag)

            if self.cache_service:
                await self.cache_service.invalidate(CacheKeys.feature_flags()[0])
                await self.cache_service.invalidate(CacheKeys.feature_flag(flag.name)[0])

            return FeatureFlagResult(
                name=flag.name,
                enabled=flag.enabled,
                description=flag.description,
                created_at=flag.created_at,
                updated_at=flag.updated_at,
            )
