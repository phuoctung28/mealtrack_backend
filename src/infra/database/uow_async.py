"""Async Unit of Work backed by asyncpg + AsyncSession."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.infra.database.config_async import AsyncSessionLocal
from src.infra.repositories.meal_repository_async import AsyncMealRepository
from src.infra.repositories.user_repository_async import AsyncUserRepository
from src.infra.repositories.weekly_budget_repository_async import AsyncWeeklyBudgetRepository
from src.infra.repositories.cheat_day_repository_async import AsyncCheatDayRepository
from src.infra.repositories.subscription_repository_async import AsyncSubscriptionRepository
from src.infra.repositories.notification_repository_async import AsyncNotificationRepository
from src.infra.repositories.saved_suggestion_db_repository_async import AsyncSavedSuggestionDbRepository

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
        self._init_repositories()
        return self

    def _init_repositories(self):
        self.meals = AsyncMealRepository(self.session)
        self.users = AsyncUserRepository(self.session)
        self.weekly_budgets = AsyncWeeklyBudgetRepository(self.session)
        self.cheat_days = AsyncCheatDayRepository(self.session)
        self.subscriptions = AsyncSubscriptionRepository(self.session)
        self.notifications = AsyncNotificationRepository(self.session)
        self.saved_suggestions = AsyncSavedSuggestionDbRepository(self.session)
        self.saved_suggestions_db = self.saved_suggestions  # alias for handlers using this name

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
