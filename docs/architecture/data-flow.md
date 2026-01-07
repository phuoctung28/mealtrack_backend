# Data Flow & Patterns

Patterns used for data processing and communication.

## CQRS (Command Query Responsibility Segregation)

Separate paths for "Write" operations (Commands) and "Read" operations (Queries).

- **Commands**: Modify state, publish events (e.g., `CreateMealCommand`).
- **Queries**: Read state, optimized with caching and eager loading (e.g., `GetMealQuery`).

## Event-Driven Architecture

Decouples side effects from primary business logic.

1. **Domain Event** is published by a Command Handler.
2. **Event Handlers** subscribe to specific events.
3. **Actions**: Send push notifications, invalidate cache, update analytics.

## Query Optimization (N+1 Prevention)

Uses SQLAlchemy eager loading strategies:
- `joinedload()`: For Many-to-One (User on Meal).
- `selectinload()`: For One-to-Many (FoodItems on Meal).

## Session-Based Suggestions (Phase 06)

Implemented for real-time meal recommendations.
- **TTL**: 4 hours in Redis.
- **Flow**: Generate 3 suggestions → Accept/Reject → Track session state.
