"""
Simple in-memory event bus implementation.
"""
import logging
from typing import Any, Type, Dict, List, Callable, Awaitable

from src.app.events.base import Event, DomainEvent, EventHandler
from .event_bus import EventBus

logger = logging.getLogger(__name__)


class SimpleEventBus(EventBus):
    """
    Simple in-memory event bus implementation.
    
    This is a lightweight alternative to PyMediatorEventBus that doesn't require
    external dependencies like pymediator.
    """
    
    def __init__(self):
        self._handlers: Dict[Type[Event], EventHandler] = {}
        self._subscribers: Dict[Type[DomainEvent], List[Callable[[DomainEvent], Awaitable[None]]]] = {}
    
    async def send(self, event: Event) -> Any:
        """Send a command/query and wait for the result."""
        event_type = type(event)
        
        if event_type not in self._handlers:
            raise ValueError(f"No handler registered for event type: {event_type.__name__}")
        
        handler = self._handlers[event_type]
        
        try:
            logger.debug(f"Sending event {event_type.__name__} to handler {handler.__class__.__name__}")
            result = await handler.handle(event)
            logger.debug(f"Event {event_type.__name__} handled successfully")
            return result
        except Exception as e:
            logger.error(f"Error handling event {event_type.__name__}: {str(e)}")
            raise
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to all subscribers."""
        event_type = type(event)
        
        if event_type not in self._subscribers:
            logger.debug(f"No subscribers for domain event: {event_type.__name__}")
            return
        
        subscribers = self._subscribers[event_type]
        
        for subscriber in subscribers:
            try:
                logger.debug(f"Publishing domain event {event_type.__name__} to subscriber")
                await subscriber(event)
            except Exception as e:
                logger.error(f"Error in domain event subscriber for {event_type.__name__}: {str(e)}")
                # Continue with other subscribers even if one fails
                continue
    
    def register_handler(self, event_type: Type[Event], handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        if event_type in self._handlers:
            logger.warning(f"Overriding existing handler for event type: {event_type.__name__}")
        
        self._handlers[event_type] = handler
        logger.debug(f"Registered handler {handler.__class__.__name__} for event type {event_type.__name__}")
    
    def subscribe(self, event_type: Type[DomainEvent], handler: Callable[[DomainEvent], Awaitable[None]]) -> None:
        """Subscribe to domain events."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler to domain event type {event_type.__name__}")
    
    def get_handler_count(self) -> int:
        """Get the number of registered handlers (for debugging)."""
        return len(self._handlers)
    
    def get_subscriber_count(self) -> int:
        """Get the total number of domain event subscribers (for debugging)."""
        return sum(len(subscribers) for subscribers in self._subscribers.values()) 