"""
Unit of Work pattern implementation for managing database transactions.
"""
from typing import TypeVar

from sqlalchemy.orm import Session

from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.infra.repositories.chat_repository import ChatRepository
from src.infra.repositories.meal_plan_repository import MealPlanRepository
from src.infra.repositories.meal_repository import MealRepository
from src.infra.repositories.meal_suggestion_repository import MealSuggestionRepository
from src.infra.repositories.notification_repository import NotificationRepository
from src.infra.repositories.subscription_repository import SubscriptionRepository
from src.infra.repositories.user_repository import UserRepository

T = TypeVar('T')


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
        self.meal_suggestions = MealSuggestionRepository(session)
        self.meal_plans = MealPlanRepository(session)
        self.chats = ChatRepository(session)
        
    def __enter__(self) -> 'UnitOfWork':
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
                self.commit()
        finally:
            self.session.close()
    
    async def __aenter__(self) -> 'UnitOfWork':
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