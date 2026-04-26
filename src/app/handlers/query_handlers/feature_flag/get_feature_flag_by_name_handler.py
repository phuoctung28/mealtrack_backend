"""Handler for getting a feature flag by name."""

import logging
from typing import Optional

from sqlalchemy import select

from src.app.events.base import EventHandler, handles
from src.app.queries.feature_flag.get_feature_flag_by_name_query import (
    GetFeatureFlagByNameQuery,
    FeatureFlagResult,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.infra.cache.cache_service import CacheService
from src.infra.database.models.feature_flag import FeatureFlag
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


class FeatureFlagNotFoundError(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Feature flag '{name}' not found")


@handles(GetFeatureFlagByNameQuery)
class GetFeatureFlagByNameQueryHandler(
    EventHandler[GetFeatureFlagByNameQuery, FeatureFlagResult]
):

    def __init__(
        self,
        uow: Optional[AsyncUnitOfWorkPort] = None,
        cache_service: Optional[CacheService] = None,
    ):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, query: GetFeatureFlagByNameQuery) -> FeatureFlagResult:
        cache_key, ttl = CacheKeys.feature_flag(query.name)
        if self.cache_service:
            cached = await self.cache_service.get_json(cache_key)
            if cached:
                return FeatureFlagResult(**cached)

        uow = self.uow or AsyncUnitOfWork()
        async with uow:
            result = await uow.session.execute(
                select(FeatureFlag).where(FeatureFlag.name == query.name)
            )
            flag = result.scalars().first()

            if not flag:
                raise FeatureFlagNotFoundError(query.name)

            response = FeatureFlagResult(
                name=flag.name,
                enabled=flag.enabled,
                description=flag.description,
                created_at=flag.created_at,
                updated_at=flag.updated_at,
            )

            if self.cache_service:
                await self.cache_service.set_json(
                    cache_key,
                    {
                        "name": response.name,
                        "enabled": response.enabled,
                        "description": response.description,
                        "created_at": response.created_at.isoformat(),
                        "updated_at": response.updated_at.isoformat(),
                    },
                    ttl,
                )

            return response
