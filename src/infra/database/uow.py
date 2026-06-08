"""
Unit of Work pattern implementation for managing database transactions.
"""

from typing import TypeVar

from sqlalchemy.orm import Session

from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.domain.ports.meal_suggestion_repository_port import (
    MealSuggestionRepositoryPort,
)
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.infra.repositories.cheat_day_repository import CheatDayRepository
from src.infra.repositories.meal_repository import MealRepository
from src.infra.repositories.notification_repository import NotificationRepository
from src.infra.repositories.saved_suggestion_db_repository import (
    SavedSuggestionDbRepository,
)
from src.infra.repositories.subscription_repository import SubscriptionRepository
from src.infra.repositories.user_repository import UserRepository
from src.infra.repositories.weekly_budget_repository import WeeklyBudgetRepository

T = TypeVar("T")


class UnavailableMealSuggestionSessionStore(MealSuggestionRepositoryPort):
    """Placeholder for Redis-backed suggestion sessions outside DB transactions."""

    @staticmethod
    def _raise() -> None:
        raise RuntimeError(
            "Meal suggestion sessions are Redis-backed transient state. "
            "Use src.api.base_dependencies.get_meal_suggestion_repository() "
            "instead of UnitOfWork.meal_suggestions."
        )

    async def save_session(self, session: SuggestionSession) -> None:
        self._raise()

    async def get_session(self, session_id: str) -> SuggestionSession | None:
        self._raise()

    async def update_session(self, session: SuggestionSession) -> None:
        self._raise()

    async def delete_session(self, session_id: str) -> None:
        self._raise()

    async def save_suggestions(self, suggestions: list[MealSuggestion]) -> None:
        self._raise()

    async def get_suggestion(self, suggestion_id: str) -> MealSuggestion | None:
        self._raise()

    async def update_suggestion(self, suggestion: MealSuggestion) -> None:
        self._raise()


class UnitOfWork(UnitOfWorkPort):
    """
    SQLAlchemy implementation of Unit of Work.
    """

    def __init__(self, session: Session = None):
        self.session = session
        # Repositories are initialized in __enter__ if session is created there,
        # or here if session is passed.
        if self.session:
            self._init_repositories(self.session)

    def _init_repositories(self, session: Session):
        self.users = UserRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.notifications = NotificationRepository(session)
        self.meals = MealRepository(session)
        self.meal_suggestions = UnavailableMealSuggestionSessionStore()
        self.weekly_budgets = WeeklyBudgetRepository(session)
        self.saved_suggestions_db = SavedSuggestionDbRepository(session)
        self.saved_suggestions = self.saved_suggestions_db
        self.cheat_days = CheatDayRepository(session)

    def __enter__(self) -> "UnitOfWork":
        """Enter context - start transaction."""
        if not self.session:
            # Default session handling - import here to avoid circular imports
            from src.infra.database.config import SessionLocal

            self.session = SessionLocal()
            self._init_repositories(self.session)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - commit or rollback transaction."""
        try:
            if exc_type:
                self.rollback()
            else:
                try:
                    self.commit()
                except Exception:
                    self.rollback()
                    raise
        finally:
            self.session.close()

    async def __aenter__(self) -> "UnitOfWork":
        """Support async context manager for compatibility."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support async context manager for compatibility."""
        return self.__exit__(exc_type, exc_val, exc_tb)

    def commit(self):
        """Commit the transaction."""
        self.session.commit()

    async def commit_async(self):
        """Async wrapper for commit."""
        self.commit()

    def rollback(self):
        """Rollback the transaction."""
        self.session.rollback()

    async def rollback_async(self):
        """Async wrapper for rollback."""
        self.rollback()

    def refresh(self, obj):
        """Refresh an object from the database."""
        self.session.refresh(obj)
