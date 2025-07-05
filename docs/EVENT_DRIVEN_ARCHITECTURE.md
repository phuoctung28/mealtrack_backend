# Event-Driven Architecture in MealTrack

## Overview

This document explains the event-driven architecture implementation that reduces coupling between API routes and business logic handlers.

## Architecture Comparison

### Before: Direct Coupling
```python
# API Route directly depends on handler
@router.post("/meals/image")
async def upload_meal_image(
    file: UploadFile,
    handler: MealHandler = Depends(get_meal_handler)  # Direct dependency
):
    # Business logic mixed with HTTP concerns
    result = handler.upload_image(file)
    return {"meal_id": result.meal_id}
```

### After: Event-Driven Decoupling
```python
# API Route only depends on event bus
@router.post("/meals/image")
async def upload_meal_image(
    file: UploadFile,
    event_bus: EventBus = Depends(get_configured_event_bus)  # Only event bus dependency
):
    # Create command/event
    command = UploadMealImageCommand(
        file_contents=contents,
        content_type=file.content_type
    )
    
    # Send to event bus
    result = await event_bus.send(command)
    return {"meal_id": result["meal_id"]}
```

## Benefits

### 1. **Loose Coupling**
- API routes don't know about specific handlers
- Easy to swap implementations
- Better testability

### 2. **Clear Separation of Concerns**
- Routes: HTTP/REST concerns only
- Commands/Queries: Business intent
- Handlers: Business logic
- Events: Side effects and integration

### 3. **Event Sourcing Ready**
- Domain events can be stored for audit trail
- Easy to add event replay functionality
- Natural fit for CQRS pattern

### 4. **Extensibility**
- New features via event subscribers
- No modification to existing code
- Plugin-like architecture

## Implementation Structure

```
src/
├── api/
│   ├── routes/          # API endpoints (thin controllers)
│   └── dependencies/
│       └── event_bus.py # Event bus configuration
├── app/
│   ├── events/          # Event definitions
│   │   ├── base.py      # Base classes (Event, Command, Query)
│   │   ├── meal_events.py
│   │   └── tdee_events.py
│   └── event_handlers/  # Event handlers
│       ├── meal_handlers.py
│       └── tdee_handlers.py
```

## Event Types

### 1. **Commands** (Change State)
```python
@dataclass
class UploadMealImageCommand(Command):
    file_contents: bytes
    content_type: str
```

### 2. **Queries** (Read State)
```python
@dataclass
class GetMealByIdQuery(Query):
    meal_id: str
```

### 3. **Domain Events** (Things That Happened)
```python
@dataclass
class MealImageUploadedEvent(DomainEvent):
    meal_id: str
    image_url: str
    upload_timestamp: datetime
```

## Usage Examples

### 1. Simple Query
```python
# In API route
query = GetMealByIdQuery(meal_id="123")
meal = await event_bus.send(query)
```

### 2. Command with Domain Events
```python
# Command handler returns domain events
result = await event_bus.send(UploadMealImageCommand(...))
# Domain events are automatically published to subscribers
```

### 3. Event Subscription
```python
@subscribes_to(MealImageUploadedEvent)
async def trigger_analysis(event: MealImageUploadedEvent):
    # Automatically called when event is published
    print(f"Starting analysis for meal {event.meal_id}")
```

## Testing Benefits

### Before
```python
# Need to mock specific handler and all its dependencies
mock_handler = Mock(spec=MealHandler)
mock_handler.upload_image.return_value = ...
```

### After
```python
# Just configure event bus with test handlers
event_bus = EventBus()
event_bus.register_handler(UploadMealImageCommand, TestUploadHandler())
```

## Migration Path

1. **Phase 1**: Implement event bus alongside existing code
2. **Phase 2**: Gradually migrate endpoints to use events
3. **Phase 3**: Remove direct handler dependencies
4. **Phase 4**: Add domain event publishing

## Best Practices

1. **Keep Events Immutable**: Use `@dataclass` with frozen=True
2. **Version Events**: Add version field for future compatibility
3. **Avoid Large Payloads**: Store references, not full objects
4. **Use Correlation IDs**: Track related events across services
5. **Log All Events**: Built-in audit trail

## Future Enhancements

1. **Event Store**: Persist all events for replay
2. **Async Processing**: Background event processing
3. **Event Streaming**: Kafka/RabbitMQ integration
4. **Distributed Tracing**: Track events across services
5. **Event Versioning**: Handle event schema evolution