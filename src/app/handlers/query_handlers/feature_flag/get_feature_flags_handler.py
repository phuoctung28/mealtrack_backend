"""Handler for getting all feature flags."""

import logging
from typing import Optional

from sqlalchemy import select

from src.app.events.base import EventHandler, handles
from src.app.queries.feature_flag.get_feature_flags_query import (
    GetFeatureFlagsQuery,
    FeatureFlagsResult,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService
from src.infra.database.models.feature_flag import FeatureFlag
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(GetFeatureFlagsQuery)
class GetFeatureFlagsQueryHandler(
    EventHandler[GetFeatureFlagsQuery, FeatureFlagsResult]
):

    def __init__(
        self,
        uow: Optional[AsyncUnitOfWorkPort] = None,
        cache_service: Optional[CacheService] = None,
    ):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, query: GetFeatureFlagsQuery) -> FeatureFlagsResult:
        cache_key, ttl = CacheKeys.feature_flags()
        if self.cache_service:
            cached = await self.cache_service.get_json(cache_key)
            if cached:
                return FeatureFlagsResult(
                    flags=cached["flags"],
                    updated_at=cached["updated_at"],
                )

        uow = self.uow or AsyncUnitOfWork()
        async with uow:
            result = await uow.session.execute(select(FeatureFlag))
            feature_flags = result.scalars().all()
            flags_dict = {flag.name: flag.enabled for flag in feature_flags}

            response = FeatureFlagsResult(flags=flags_dict, updated_at=utc_now())

            if self.cache_service:
                await self.cache_service.set_json(
                    cache_key,
                    {"flags": flags_dict, "updated_at": response.updated_at.isoformat()},
                    ttl,
                )

            return response
