"""
PyMediator-based event bus implementation.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Type, TypeVar, Dict, List

from pymediator import Mediator as PyMediator, SingletonRegistry

from src.app.events.base import Event, DomainEvent, EventHandler
from .event_bus import EventBus

logger = logging.getLogger(__name__)

T = TypeVar('T')

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
        self._thread_pool = ThreadPoolExecutor(max_workers=20, thread_name_prefix="EventBus")
        
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
            
            result = await asyncio.get_event_loop().run_in_executor(
                self._thread_pool, 
                self._mediator.send, 
                wrapped_request
            )
            
            # Handle domain events if returned
            if isinstance(result, list) and all(isinstance(e, DomainEvent) for e in result):
                logger.info(f"Publishing {len(result)} domain events from command result")
                for domain_event in result:
                    await self.publish(domain_event)
            elif isinstance(result, dict) and 'events' in result:
                events = result.get('events', [])
                logger.info(f"Publishing {len(events)} domain events from command result")
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
            # Execute all tasks in the background (fire-and-forget)
            async def run_tasks_in_background():
                logger.info(f"Starting background processing for {event_type.__name__}")
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log any exceptions
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(
                            f"Subscriber {i} for {event_type.__name__} failed: {result}",
                            exc_info=result
                        )
                logger.info(f"Background processing completed for {event_type.__name__}")
            
            # Schedule the task to run in the background
            logger.info(f"Scheduling background task for {event_type.__name__}")
            asyncio.create_task(run_tasks_in_background())

    def close(self):
        if hasattr(self, '_thread_pool'):
            self._thread_pool.shutdown(wait=True)
            logger.info("Event bus thread pool shut down")
