# Backend System Architecture Overview

**Last Updated:** May 15, 2026
**Architecture:** 4-Layer Clean + CQRS + Event-Driven
**Event Bus:** PyMediator (singleton registry pattern)
**Codebase:** 430 files, ~38.5K LOC across 4 layers

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (76 files)                    │
│  HTTP Routing │ Pydantic Validation │ Auth │ Middleware      │
└────────────────────────┬────────────────────────────────────┘
                         │ Commands/Queries
┌────────────────────────▼────────────────────────────────────┐
│              Application Layer (140 files)                   │
│  CQRS Handlers │ Event Publishing │ App Services             │
└────────────────────────┬────────────────────────────────────┘
                         │ Domain Services
┌────────────────────────▼────────────────────────────────────┐
│                Domain Layer (133 files)                      │
│  Business Logic │ Domain Models │ Port Interfaces            │
└────────────────────────┬────────────────────────────────────┘
                         │ Port Implementations
┌────────────────────────▼────────────────────────────────────┐
│            Infrastructure Layer (80 files)                   │
│  DB │ Cache │ External APIs │ Event Bus │ Config             │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer Statistics

| Layer | Files | LOC | Key Contents |
|-------|-------|-----|-------------|
| API | 76 | ~8,605 | 17 route modules, 34 Pydantic schemas, 8 mappers, 3 middleware |
| App | 140 | ~6,229 | 30 commands, 31 queries, 19 events, 51+ handlers, 3 app services |
| Domain | 133 | ~14,556 | 8 bounded contexts, 30+ entities, 50+ services, 17 port interfaces |
| Infra | 80 | ~8,895 | 13+ DB tables, 10+ repos, Redis, PyMediator, external adapters |
| **Total** | **430** | **~38,300** | |

**Layer rule:** Domain has ZERO external dependencies. See `cqrs-guide.md` for handler patterns.

---

## Key Architectural Patterns

### Dependency Inversion
Domain defines port interfaces; infrastructure implements them. Handlers depend on abstractions.

### CQRS
- **Commands** — write operations, publish events (CreateMeal, UpdateUserMetrics)
- **Queries** — read-only, return immediately (GetMealById, SearchFoods)
- **Events** — fire-and-forget, processed async (MealCreated, UserOnboarded)

### Event Bus (PyMediator Singleton)
```python
result = await event_bus.send(CreateMealCommand(...))    # synchronous
await event_bus.publish(MealCreatedEvent(...))           # fire-and-forget
```

### Repository Pattern
Smart sync (diff-based updates), eager loading via pre-defined `joinedload` options.

---

## Bounded Contexts (Domain)

| Context | Key Entities |
|---------|-------------|
| Meal | Meal (state machine), MealImage, Ingredient |
| Nutrition | Nutrition, FoodItem, Macros, Micros |
| User | User, UserProfile, Activity, TdeeRequest |
| Meal Planning | MealPlan, PlannedMeal, DayPlan, UserPreferences |
| Conversation | Conversation, Message, ConversationState |
| Notification | UserFcmToken, NotificationPreferences, PushNotification |
| AI | GPTAnalysisResponse, GPTFoodItem, GPTResponseError |
| Chat | Thread, Message, ThreadStatus, MessageRole |

---

## Data Flow Example: Meal Analysis

1. `POST /v1/meals/image/analyze` receives image
2. Route creates `UploadMealImageImmediatelyCommand`
3. `EventBus.send()` → `UploadMealImageImmediatelyHandler`
4. Handler uploads to Cloudinary, creates Meal (PROCESSING), publishes `MealImageUploadedEvent`
5. Handler returns Meal immediately to API (synchronous response to client)
6. `EventBus.publish()` → `MealAnalysisEventHandler` (background)
7. Background: calls `VisionAIService` (Gemini), parses nutrition, updates Meal to READY

---

## Known Issues

- CORS `allow_origins=["*"]` wide open in production (security risk)
- Premium features not restricted on routes (`require_premium` dependency not applied)
- No API versioning strategy beyond v1
- `CloudinaryImageStore` instantiated directly in routes (not via DI)
- Hardcoded constants (MAX_FILE_SIZE, SLOW_REQUEST_THRESHOLD) not in config
- `AsyncUnitOfWork` uses `asyncio.Lock`; concurrent reuse within one instance will block (by design — use separate instances per handler, enforced by event bus handler cloning)

---

See related: `cqrs-guide.md`, `database-guide.md`, `external-services.md`, `code-standards.md`
