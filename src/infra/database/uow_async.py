"""Async Unit of Work backed by asyncpg + AsyncSession."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.infra.database.config_async import AsyncSessionLocal

logger = logging.getLogger(__name__)


class AsyncUnitOfWork(AsyncUnitOfWorkPort):
    """SQLAlchemy AsyncSession Unit of Work.

    Usage:
        async with AsyncUnitOfWork() as uow:
            result = await uow.meals.find_by_id(meal_id)
    """

    def __init__(self):
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "AsyncUnitOfWork":
        self.session = AsyncSessionLocal()
        await self.session.__aenter__()
        self._init_repositories()
        return self

    def _init_repositories(self):
        # Repositories added in Task 8 once all async repos exist.
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if exc_type:
                await self.rollback()
            else:
                try:
                    await self.commit()
                except Exception:
                    await self.rollback()
                    raise
        finally:
            await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def refresh(self, obj) -> None:
        await self.session.refresh(obj)
