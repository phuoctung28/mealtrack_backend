"""Async Unit of Work backed by asyncpg + AsyncSession."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.infra.database.config_async import AsyncSessionLocal
from src.infra.repositories.meal_repository_async import AsyncMealRepository
from src.infra.repositories.user_repository_async import AsyncUserRepository
from src.infra.repositories.weekly_budget_repository_async import (
    AsyncWeeklyBudgetRepository,
)
from src.infra.repositories.cheat_day_repository_async import AsyncCheatDayRepository
from src.infra.repositories.subscription_repository_async import (
    AsyncSubscriptionRepository,
)
from src.infra.repositories.notification_repository_async import (
    AsyncNotificationRepository,
)
from src.infra.repositories.saved_suggestion_db_repository_async import (
    AsyncSavedSuggestionDbRepository,
)

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
        if AsyncSessionLocal is None:
            raise RuntimeError(
                "AsyncSessionLocal is not initialized. Async engine setup failed; "
                "check async DB configuration."
            )
        self.session = AsyncSessionLocal()
        self._init_repositories()
        return self

    def _init_repositories(self):
        session = self._require_session()
        self.meals = AsyncMealRepository(session)
        self.users = AsyncUserRepository(session)
        self.weekly_budgets = AsyncWeeklyBudgetRepository(session)
        self.cheat_days = AsyncCheatDayRepository(session)
        self.subscriptions = AsyncSubscriptionRepository(session)
        self.notifications = AsyncNotificationRepository(session)
        self.saved_suggestions = AsyncSavedSuggestionDbRepository(session)
        self.saved_suggestions_db = (
            self.saved_suggestions
        )  # alias for handlers using this name

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        session = self.session
        if session is None:
            return
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
            await session.close()
            self.session = None

    async def commit(self) -> None:
        await self._require_session().commit()

    async def rollback(self) -> None:
        await self._require_session().rollback()

    async def refresh(self, obj) -> None:
        await self._require_session().refresh(obj)

    def _require_session(self) -> AsyncSession:
        if self.session is None:
            raise RuntimeError("AsyncUnitOfWork session is not initialized.")
        return self.session
