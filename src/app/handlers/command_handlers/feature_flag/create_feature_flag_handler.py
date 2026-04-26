"""Handler for creating a feature flag."""

import logging
from typing import Optional

from sqlalchemy import select

from src.app.commands.feature_flag.create_feature_flag_command import (
    CreateFeatureFlagCommand,
)
from src.app.events.base import EventHandler, handles
from src.app.queries.feature_flag.get_feature_flag_by_name_query import (
    FeatureFlagResult,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.infra.cache.cache_service import CacheService
from src.infra.database.models.feature_flag import FeatureFlag
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


class FeatureFlagExistsError(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Feature flag '{name}' already exists")


@handles(CreateFeatureFlagCommand)
class CreateFeatureFlagCommandHandler(
    EventHandler[CreateFeatureFlagCommand, FeatureFlagResult]
):

    def __init__(
        self,
        uow: Optional[AsyncUnitOfWorkPort] = None,
        cache_service: Optional[CacheService] = None,
    ):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, command: CreateFeatureFlagCommand) -> FeatureFlagResult:
        uow = self.uow or AsyncUnitOfWork()
        async with uow:
            result = await uow.session.execute(
                select(FeatureFlag).where(FeatureFlag.name == command.name)
            )
            existing = result.scalars().first()
            if existing:
                raise FeatureFlagExistsError(command.name)

            new_flag = FeatureFlag(
                name=command.name,
                enabled=command.enabled,
                description=command.description,
            )

            uow.session.add(new_flag)
            await uow.commit()
            await uow.session.refresh(new_flag)

            if self.cache_service:
                await self.cache_service.invalidate(CacheKeys.feature_flags()[0])
                await self.cache_service.invalidate(
                    CacheKeys.feature_flag(new_flag.name)[0]
                )

            return FeatureFlagResult(
                name=new_flag.name,
                enabled=new_flag.enabled,
                description=new_flag.description,
                created_at=new_flag.created_at,
                updated_at=new_flag.updated_at,
            )
