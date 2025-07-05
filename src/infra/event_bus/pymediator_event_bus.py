"""
PyMediator-based event bus implementation.
"""
import asyncio
import logging
from typing import Any, Type, TypeVar, Dict, List

from pymediator import Mediator as PyMediator, SingletonRegistry

from src.app.events.base import Event, DomainEvent, EventHandler
from .event_bus import EventBus

logger = logging.getLogger(__name__)

T = TypeVar('T')


class EventRequest:
    """Wrapper to make our Events compatible with pymediator Request protocol."""
    def __init__(self, event: Event):
        self._event = event
    
    @property
    def event(self) -> Event:
        return self._event


class PyMediatorHandlerAdapter:
    """Adapter to make our EventHandlers compatible with pymediator Handler protocol."""
    
    def __init__(self, event_handler: EventHandler):
        self._event_handler = event_handler
    
    def handle(self, request: Any) -> Any:
        """Handle the request by delegating to our event handler."""
        # Extract the actual event from the wrapper
        if hasattr(request, 'event'):
            actual_event = request.event
        else:
            actual_event = request
            
        # Check if the handler is async
        import inspect
        if inspect.iscoroutinefunction(self._event_handler.handle):
            # Create a new event loop for this thread
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context but need to return sync
                # This shouldn't happen with our current setup
                return None
            except RuntimeError:
                # No event loop, create one
                return asyncio.run(self._event_handler.handle(actual_event))
        else:
            return self._event_handler.handle(actual_event)


class AsyncPyMediatorHandlerAdapter:
    """Async-aware adapter for our EventHandlers."""
    
    def __init__(self, event_handler: EventHandler):
        self._event_handler = event_handler
    
    async def handle(self, request: Any) -> Any:
        """Handle the request asynchronously."""
        # Extract the actual event from the wrapper
        if hasattr(request, 'event'):
            actual_event = request.event
        else:
            actual_event = request
            
        return await self._event_handler.handle(actual_event)


class PyMediatorEventBus(EventBus):
    """
    Event bus implementation using pymediator library.
    
    This implementation wraps pymediator to provide compatibility with our
    event-driven architecture while leveraging pymediator's features.
    """
    
    def __init__(self):
        # Use SingletonRegistry to ensure handlers are reused
        registry = SingletonRegistry()
        self._mediator = PyMediator(registry=registry)
        self._event_type_mapping: Dict[Type[Event], Type[EventRequest]] = {}
        self._domain_event_subscribers: Dict[Type[DomainEvent], List[Any]] = {}
        
    def register_handler(self, event_type: Type[Event], handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        # Create a unique wrapper class for this event type
        wrapper_class = type(
            f"{event_type.__name__}Request",
            (EventRequest,),
            {
                '__init__': lambda self, event: EventRequest.__init__(self, event)
            }
        )
        
        # Store the mapping
        self._event_type_mapping[event_type] = wrapper_class
        
        # Create handler adapter - we'll handle async inside the adapter
        adapter_class = type(
            f"{handler.__class__.__name__}Adapter",
            (PyMediatorHandlerAdapter,),
            {
                '__init__': lambda self: PyMediatorHandlerAdapter.__init__(self, handler)
            }
        )
        
        # Register with pymediator
        self._mediator.registry.register(wrapper_class, adapter_class)
        
        logger.info(f"Registered {handler.__class__.__name__} for {event_type.__name__}")
    
    def subscribe(self, event_type: Type[DomainEvent], handler) -> None:
        """Subscribe to domain events."""
        if event_type not in self._domain_event_subscribers:
            self._domain_event_subscribers[event_type] = []
        
        self._domain_event_subscribers[event_type].append(handler)
        logger.info(f"Subscribed to {event_type.__name__}")
    
    async def send(self, event: Event) -> Any:
        """Send a command/query and get the result."""
        event_type = type(event)
        
        if event_type not in self._event_type_mapping:
            raise ValueError(f"No handler registered for {event_type.__name__}")
        
        try:
            # Wrap the event in a request
            wrapper_class = self._event_type_mapping[event_type]
            wrapped_request = wrapper_class(event)
            
            # Send through pymediator
            # Since pymediator is sync, we need to handle async carefully
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                self._mediator.send, 
                wrapped_request
            )
            
            # Handle domain events if returned
            if isinstance(result, list) and all(isinstance(e, DomainEvent) for e in result):
                for domain_event in result:
                    await self.publish(domain_event)
            elif isinstance(result, dict) and 'events' in result:
                events = result.get('events', [])
                for domain_event in events:
                    if isinstance(domain_event, DomainEvent):
                        await self.publish(domain_event)
            return result
            
        except Exception as e:
            logger.error(f"Error handling {event_type.__name__}: {str(e)}", exc_info=True)
            raise
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to all subscribers."""
        event_type = type(event)
        
        if event_type not in self._domain_event_subscribers:
            logger.debug(f"No subscribers for {event_type.__name__}")
            return
        
        subscribers = self._domain_event_subscribers[event_type]
        logger.debug(f"Publishing {event_type.__name__} to {len(subscribers)} subscribers")
        
        # Execute subscribers concurrently
        tasks = []
        for subscriber in subscribers:
            if asyncio.iscoroutinefunction(subscriber):
                tasks.append(subscriber(event))
            else:
                # Wrap sync handlers in async
                async def async_wrapper(handler, evt):
                    return handler(evt)
                tasks.append(async_wrapper(subscriber, event))
        
        if tasks:
            # Execute all tasks and capture exceptions
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Subscriber {i} for {event_type.__name__} failed: {result}",
                        exc_info=result
                    )