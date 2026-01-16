from abc import ABC, abstractmethod
from typing import TypeVar, Optional

from src.domain.ports.user_repository_port import UserRepositoryPort
from src.domain.ports.subscription_repository_port import SubscriptionRepositoryPort
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.meal_suggestion_repository_port import MealSuggestionRepositoryPort
from src.domain.ports.meal_plan_repository_port import MealPlanRepositoryPort
from src.domain.ports.chat_repository_port import ChatRepositoryPort

T = TypeVar('T')


class UnitOfWorkPort(ABC):
    """
    Interface for Unit of Work.
    Manages transactions and provides access to repositories.
    """
    
    users: UserRepositoryPort
    subscriptions: SubscriptionRepositoryPort
    notifications: NotificationRepositoryPort
    meals: MealRepositoryPort
    meal_suggestions: MealSuggestionRepositoryPort
    meal_plans: MealPlanRepositoryPort
    chats: ChatRepositoryPort
    
    @abstractmethod
    def __enter__(self) -> 'UnitOfWorkPort':
        """Enter the runtime context related to this object."""
        pass
    
    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the runtime context related to this object."""
        pass
    
    @abstractmethod
    def commit(self) -> None:
        """Commit the transaction."""
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        """Rollback the transaction."""
        pass
    
    @abstractmethod
    def refresh(self, obj: T) -> None:
        """Refresh an object from the persistence store."""
        pass