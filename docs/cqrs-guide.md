# Backend CQRS Pattern Guide

**Last Updated:** June 17, 2026
**Event Bus:** PyMediator with singleton registry pattern
**Handlers:** 87 handler files across commands, queries, and events
**Domains:** Activity, Cheat Day, Codes, Daily Meal, Food, Hydration, Ingredient, Meal, Meal Plan, Meal Suggestion, Movement, Notification, Nutrition, Promo Code, Referral, Saved Suggestion, TDEE, User, Weight

---

## Architecture Layers

```
API Layer (routes)
    ↓ commands/queries
Application Layer (CQRS handlers + App Services)
    ↓ domain services
Domain Layer (business logic)
    ↓ port implementations
Infrastructure Layer (DB, external APIs)
```

Each layer has ZERO knowledge of layers above it. Domain layer is completely independent.

---

## Commands (Write Operations)

Named with imperative verbs. Validated in `__post_init__()`. Return domain entity or None.

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

**Naming:** Create, Update, Delete, Generate, Register, Upload, Sync

---

## Queries (Read Operations)

Named with "Get" or "Search". No side effects. Return domain entity, list, or DTO.

```python
@dataclass
class GetMealByIdQuery(Query):
    meal_id: str
    user_id: str
```

**Naming:** GetXById, SearchXBy, ListX

---

## Events (Domain Events)

Named with past tense verbs. Immutable historical facts for audit trail and downstream processing.

```python
@dataclass
class MealCreatedEvent(DomainEvent):
    aggregate_id: str
    meal_id: str
    user_id: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())
```

**Naming:** Created, Updated, Deleted, Generated, Analyzed

---

## Handler Pattern

All three types share the same decorator and base class:

```python
@handles(UpdateUserMetricsCommand)
class UpdateUserMetricsCommandHandler(EventHandler[UpdateUserMetricsCommand, User]):
    def __init__(self, user_repo: UserRepositoryPort):
        self.user_repo = user_repo

    async def handle(self, command: UpdateUserMetricsCommand) -> User:
        ...
```

Event handlers return `None` (side effects only — notifications, jobs, etc.).

---

## PyMediator Event Bus

### Singleton Registry Pattern

```python
# Initialize once at app startup — prevents memory leaks from dynamic class generation
event_bus = PyMediatorEventBus()

result = await event_bus.send(CreateMealCommand(...))   # command/query
await event_bus.publish(MealCreatedEvent(...))          # fire-and-forget
```

### Two Event Buses

1. **Food Search Bus**: Lightweight, food queries only
2. **Configured Bus**: Full CQRS bus registered from `src/api/dependencies/event_bus.py`

---

## Usage from Routes

```python
@router.post("/meals")
async def create_meal(
    request: CreateMealRequest,
    event_bus: EventBus = Depends(get_event_bus),
):
    meal = await event_bus.send(CreateMealCommand(user_id=user.id, ...))
    return meal
```

---

## Transaction Management

```python
class UnitOfWork:
    async def __aenter__(self): ...   # Begin transaction
    async def __aexit__(self, exc_type, exc, tb):
        if exc: ...   # Rollback
        else: ...     # Commit + invalidate caches
```

### AsyncUnitOfWork Concurrency Guard

`AsyncUnitOfWork` uses `asyncio.Lock` to prevent the same instance from being entered concurrently. If two coroutines attempt `async with uow:` simultaneously, the second will block until the first exits (commit/rollback + session close + lock release).

To prevent shared-state bugs across handlers, the event bus clones each handler before dispatch — every `event_bus.send()` call receives a fresh `AsyncUnitOfWork` instance.

```python
# Correct — each call gets an isolated session
async with AsyncUnitOfWork() as uow:
    result = await uow.meals.find_by_id(meal_id)
```

---

## Key Rules

| Rule | Applies To |
|------|-----------|
| Single responsibility: one use case per command/query | Commands, Queries |
| Validation in `__post_init__()` | Commands |
| Never change state | Queries, Events |
| Always async | All handlers |
| Fire-and-forget (no wait) | Events |

---

See related: `code-standards.md`, `system-architecture.md`, `testing-standards.md`
