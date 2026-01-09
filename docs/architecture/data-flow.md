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

## Multilingual Meal Suggestions (Phase 01)

Language parameter flows through entire suggestion pipeline:

1. **API Layer** (`MealSuggestionRequest.language`)
   - Validated by `validate_language_code()` field validator
   - Defaults to "en"
   - Valid codes: en, vi, es, fr, de, ja, zh
   - Invalid codes fallback to "en" with warning

2. **Command Layer** (`GenerateMealSuggestionsCommand.language`)
   - Carries language from request to handler

3. **Handler Layer** (`GenerateMealSuggestionsCommandHandler`)
   - Passes language to `SuggestionOrchestrationService.generate_suggestions()`

4. **Domain Layer** (`SuggestionOrchestrationService`)
   - Accepts `language: str = "en"` parameter
   - Stores in `SuggestionSession.language`
   - Passed to meal generation service for localized output

5. **Storage** (Redis/DB)
   - Language stored with session for 4-hour lifetime
   - Persists through regeneration and user interactions

**Result**: All meal names, descriptions, and cooking instructions generated in requested language.
