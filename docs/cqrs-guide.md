# Backend CQRS Pattern Guide

**Last Updated:** April 17, 2026  
**Event Bus:** PyMediator with singleton registry pattern  
**Handlers:** 51+ across commands, queries, and events  
**Domains:** 11 (Chat, Meal, Daily Meal, Meal Plan, Meal Suggestion, User, Notification, Ingredient, TDEE, Activity, Food)

---

## Architecture Layers

```
API Layer (routes)
    ↓ commands/queries
Application Layer (CQRS handlers)
    ↓ domain services
Domain Layer (business logic)
    ↓ port implementations
Infrastructure Layer (DB, external APIs)
```

Each layer has ZERO knowledge of layers above it. Domain layer is completely independent.

---

## Commands (Write Operations)

Commands represent user intent to change state. Named with imperative verbs.

**Structure:**
```python
@dataclass
class UpdateUserMetricsCommand(Command):
    user_id: str
    weight_kg: float
    body_fat_percentage: Optional[float] = None

    def __post_init__(self):
        if self.weight_kg <= 0:
            raise ValidationException("Weight must be positive")
```

**Naming**: Create, Update, Delete, Generate, Register, Upload, Sync

**Validation**: In `__post_init__()` method

**Return**: Domain entity or None

**Handler Pattern:**
```python
@handles(UpdateUserMetricsCommand)
class UpdateUserMetricsCommandHandler(EventHandler[UpdateUserMetricsCommand, User]):
    def __init__(self, user_repo: UserRepositoryPort):
        self.user_repo = user_repo

    async def handle(self, command: UpdateUserMetricsCommand) -> User:
        # Execute business logic
        # Publish events if needed
        # Return result
        pass
```

---

## Queries (Read Operations)

Queries retrieve data without side effects. Named with "Get" or "Search".

**Structure:**
```python
@dataclass
class GetMealByIdQuery(Query):
    meal_id: str
    user_id: str
```

**Naming**: GetXById, SearchXBy, ListX

**Validation**: Optional (simple only)

**Return**: Domain entity, list, or DTO

**Handler Pattern:**
```python
@handles(GetMealByIdQuery)
class GetMealByIdQueryHandler(EventHandler[GetMealByIdQuery, Optional[Meal]]):
    def __init__(self, meal_repo: MealRepositoryPort):
        self.meal_repo = meal_repo

    async def handle(self, query: GetMealByIdQuery) -> Optional[Meal]:
        meal = self.meal_repo.find_by_id(query.meal_id)
        if not meal:
            return None
        return meal
```

---

## Events (Domain Events)

Events represent things that happened. Named with past tense verbs.

**Structure:**
```python
@dataclass
class MealCreatedEvent(DomainEvent):
    aggregate_id: str          # Required: meal_id
    meal_id: str
    user_id: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())
```

**Naming**: Created, Updated, Deleted, Generated, Analyzed, Replaced

**Metadata**: Always include `event_id`, `timestamp`, optional `correlation_id`

**Purpose**: Historical facts for audit trail and downstream processing

**Event Handler Pattern:**
```python
@handles(MealCreatedEvent)
class MealCreatedEventHandler(EventHandler[MealCreatedEvent, None]):
    def __init__(self, notification_service: NotificationServicePort):
        self.notification_service = notification_service

    async def handle(self, event: MealCreatedEvent) -> None:
        # Side effects only (send notifications, trigger jobs, etc.)
        # Do not return data
        pass
```

---

## PyMediator Event Bus

### Singleton Registry Pattern

```python
# Initialize once at app startup
event_bus = PyMediatorEventBus()

# Reuse across requests (prevents memory leaks from dynamic class generation)
result = await event_bus.send(CreateMealCommand(...))
await event_bus.publish(MealCreatedEvent(...))
```

### Two Event Buses

1. **Food Search Bus**: Lightweight, food queries only (no heavy services)
2. **Configured Bus**: Full CQRS with 40+ handlers registered

---

## Handler Registration

Handlers are auto-discovered via `@handles` decorator:

```python
@handles(CreateMealCommand)
class CreateMealCommandHandler:
    pass

@handles(GetMealByIdQuery)
class GetMealByIdQueryHandler:
    pass

@handles(MealCreatedEvent)
class MealCreatedEventHandler:
    pass
```

---

## Dependency Injection

### Constructor Injection
```python
class CreateMealCommandHandler:
    def __init__(
        self,
        meal_repo: MealRepositoryPort,
        image_store: ImageStorePort,
        event_bus: EventBus,
    ):
        self.meal_repo = meal_repo
        self.image_store = image_store
        self.event_bus = event_bus

    async def handle(self, command: CreateMealCommand) -> Meal:
        # Use injected dependencies
        pass
```

### Runtime Injection
```python
def set_dependencies(self, **kwargs):
    self.meal_repo = kwargs.get('meal_repo', self.meal_repo)
```

---

## Usage from Routes

### Commands (Write)
```python
@router.post("/meals")
async def create_meal(
    request: CreateMealRequest,
    event_bus: EventBus = Depends(get_event_bus),
):
    command = CreateMealCommand(
        user_id=user.id,
        image_data=request.image,
    )
    meal = await event_bus.send(command)
    return meal
```

### Queries (Read)
```python
@router.get("/meals/{id}")
async def get_meal(
    id: str,
    event_bus: EventBus = Depends(get_event_bus),
):
    query = GetMealByIdQuery(meal_id=id)
    meal = await event_bus.send(query)
    return meal
```

### Events (Fire-and-Forget)
```python
# In a handler
await self.event_bus.publish(MealCreatedEvent(
    aggregate_id=meal.id,
    meal_id=meal.id,
    user_id=meal.user_id,
))
```

---

## Transaction Management

```python
class UnitOfWork:
    async def __aenter__(self):
        # Begin transaction
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            # Rollback on error
        else:
            # Commit on success
        # Invalidate caches
```

---

## Best Practices

1. **Single Responsibility**: One command/query = one use case
2. **Immutability**: Commands/queries/events are immutable
3. **Validation**: In `__post_init__()` for commands, in handlers for queries
4. **Error Handling**: Raise domain exceptions, handle at route level
5. **Event Sourcing**: Events are immutable records of fact
6. **Async**: All handlers are async for I/O operations
7. **No Side Effects**: Queries never change state
8. **Fire-and-Forget**: Events are published async, no wait for handlers

---

See related: `code-standards.md`, `system-architecture.md`, `testing-standards.md`
