"""
Event bus interface and in-memory implementation.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar, Callable, Awaitable

from src.app.events.base import Event, DomainEvent, EventHandler

logger = logging.getLogger(__name__)

T = TypeVar('T')


class EventBus(ABC):
    """
    Abstract event bus interface.
    
    This defines the contract that all event bus implementations must follow.
    """
    
    @abstractmethod
    async def send(self, event: Event) -> Any:
        """Send a command/query and wait for the result."""
        pass
    
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to all subscribers."""
        pass
    
    @abstractmethod
    def register_handler(self, event_type: Type[Event], handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        pass
    
    @abstractmethod
    def subscribe(self, event_type: Type[DomainEvent], handler: Callable[[DomainEvent], Awaitable[None]]) -> None:
        """Subscribe to domain events."""
        pass