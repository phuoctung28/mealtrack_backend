"""
Event bus interface and in-memory implementation.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar, Dict, List, Callable, Awaitable

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


class InMemoryEventBus(EventBus):
    """
    In-memory event bus implementation.
    
    This is suitable for single-instance applications and testing.
    For production use with multiple instances, consider using a distributed event bus.
    """
    
    def __init__(self):
        self._handlers: Dict[Type[Event], EventHandler] = {}
        self._subscribers: Dict[Type[DomainEvent], List[Callable[[DomainEvent], Awaitable[None]]]] = {}
        self._middleware: List[Callable] = []
        
    def register_handler(self, event_type: Type[Event], handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        if event_type in self._handlers:
            logger.warning(f"Overwriting existing handler for {event_type.__name__}")
        self._handlers[event_type] = handler

    def subscribe(self, event_type: Type[DomainEvent], handler: Callable[[DomainEvent], Awaitable[None]]) -> None:
        """Subscribe to domain events."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed to {event_type.__name__}")
    
    def use_middleware(self, middleware: Callable) -> None:
        """Add middleware to the event processing pipeline."""
        self._middleware.append(middleware)
    
    async def send(self, event: Event) -> Any:
        """
        Send a command/query and get the result.
        
        Args:
            event: The command or query to handle
            
        Returns:
            The result from the handler
            
        Raises:
            ValueError: If no handler is registered
            Exception: Any exception raised by the handler
        """
        event_type = type(event)
        
        # Apply middleware
        processed_event = event
        for middleware in self._middleware:
            processed_event = await middleware(processed_event)
        
        # Find and execute handler
        if event_type not in self._handlers:
            raise ValueError(f"No handler registered for {event_type.__name__}")
        
        handler = self._handlers[event_type]
        logger.debug(f"Handling {event_type.__name__} with {handler.__class__.__name__}")
        
        try:
            result = await handler.handle(processed_event)
            
            # If the handler returns domain events, publish them
            if isinstance(result, list) and all(isinstance(e, DomainEvent) for e in result):
                for domain_event in result:
                    await self.publish(domain_event)
            elif isinstance(result, dict) and 'events' in result:
                # Handle case where result contains events
                events = result.get('events', [])
                for domain_event in events:
                    if isinstance(domain_event, DomainEvent):
                        await self.publish(domain_event)
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling {event_type.__name__}: {str(e)}", exc_info=True)
            raise
    
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event to all subscribers.
        
        Args:
            event: The domain event to publish
        """
        event_type = type(event)
        
        if event_type in self._subscribers:
            subscribers = self._subscribers[event_type]
            logger.debug(f"Publishing {event_type.__name__} to {len(subscribers)} subscribers")
            
            # Run all subscribers concurrently
            # Using gather with return_exceptions=True to prevent one failing subscriber
            # from affecting others
            tasks = [subscriber(event) for subscriber in subscribers]
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log any exceptions
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(
                            f"Subscriber {i} for {event_type.__name__} failed: {result}",
                            exc_info=result
                        )
        else:
            logger.debug(f"No subscribers for {event_type.__name__}")