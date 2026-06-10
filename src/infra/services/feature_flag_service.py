"""Minimal application service for feature flag writes."""

from sqlalchemy import select

from src.api.exceptions import ConflictException, ResourceNotFoundException
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.feature_flag import FeatureFlag
from src.infra.database.uow_async import AsyncUnitOfWork


class FeatureFlagService:
    """Wraps feature flag create/update with UoW transaction ownership."""

    async def create(self, name: str, enabled: bool, description: str | None) -> FeatureFlag:
        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                select(FeatureFlag).where(FeatureFlag.name == name)
            )
            if result.scalar_one_or_none():
                raise ConflictException(f"Feature flag '{name}' already exists")
            flag = FeatureFlag(name=name, enabled=enabled, description=description)
            uow.session.add(flag)
            await uow.session.flush()
            await uow.session.refresh(flag)
            return flag
        # UoW __aexit__ commits on clean exit

    async def update(self, name: str, enabled: bool | None, description: str | None) -> FeatureFlag:
        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                select(FeatureFlag).where(FeatureFlag.name == name)
            )
            flag = result.scalar_one_or_none()
            if not flag:
                raise ResourceNotFoundException(f"Feature flag '{name}' not found")
            if enabled is not None:
                flag.enabled = enabled
            if description is not None:
                flag.description = description
            flag.updated_at = utc_now()
            await uow.session.flush()
            await uow.session.refresh(flag)
            return flag
        # UoW __aexit__ commits on clean exit
