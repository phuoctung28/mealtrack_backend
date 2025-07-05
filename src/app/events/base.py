"""
Base classes for event-driven architecture.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic

logger = logging.getLogger(__name__)

# Type variable for event
TEvent = TypeVar('TEvent', bound='Event')
TResult = TypeVar('TResult')


class Event(ABC):
    """Base class for all events."""
    pass


@dataclass
class Command(Event):
    """Base class for commands (events that change state)."""
    pass


@dataclass
class Query(Event):
    """Base class for queries (events that read state)."""
    pass


class DomainEvent(Event):
    """
    Base class for domain events (things that happened).
    
    Subclasses should:
    1. Use @dataclass decorator
    2. Define aggregate_id: str as the first field
    3. Define any other required fields
    4. Add these metadata fields at the end with defaults:
       - event_id: str = field(default_factory=lambda: str(uuid4()))
       - timestamp: datetime = field(default_factory=datetime.now)
       - correlation_id: str = field(default_factory=lambda: str(uuid4()))
    """
    pass


class EventHandler(ABC, Generic[TEvent, TResult]):
    """Base class for event handlers."""
    
    @abstractmethod
    async def handle(self, event: TEvent) -> TResult:
        """Handle the event and return result."""
        pass
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for the handler. Override in subclasses if needed."""
        pass


def handles(event_type: type):
    """Decorator to mark which event type a handler handles."""
    def decorator(handler_class):
        handler_class._handles = event_type
        return handler_class
    return decorator


