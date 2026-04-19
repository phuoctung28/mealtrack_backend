# Backend System Architecture Overview

**Last Updated:** April 17, 2026  
**Architecture:** 4-Layer Clean + CQRS + Event-Driven  
**Event Bus:** PyMediator (singleton registry pattern)  
**Codebase:** 430 files, ~38.5K LOC across 4 layers

---

## Architecture Overview

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

## Layer Statistics & Responsibilities

| Layer | Files | LOC | Purpose |
|-------|-------|-----|---------|
| API | 76 | ~8,605 | HTTP presentation + routing |
| App | 140 | ~6,229 | CQRS orchestration (commands/queries/events) |
| Domain | 133 | ~14,556 | Business logic (ZERO external dependencies) |
| Infra | 80 | ~8,895 | DB, cache, external services, event bus |
| **Total** | **430** | **~38,300** | |

---

## Layer Responsibilities

### 1. API Layer (`src/api/`)
**Responsibility:** HTTP request/response handling

- **12 Route Modules**: 50+ REST endpoints (health, meals, users, profiles, chat, notifications, etc.)
- **34 Pydantic Schemas**: Request/response DTOs with validation
- **8 Mappers**: API ↔ Domain transformations
- **3 Middleware Layers**: CORS, request logging, dev auth bypass
- **Firebase JWT Auth**: Token verification with dev bypass
- **WebSocket Support**: ConnectionManager for real-time chat

**Flow:**
1. Receive HTTP request
2. Validate via Pydantic
3. Create command/query
4. Dispatch to event bus
5. Map result to response DTO
6. Return response

### 2. Application Layer (`src/app/`)
**Responsibility:** CQRS command/query/event orchestration

- **30 Commands**: Write operations across 11 domains
- **31 Queries**: Read operations
- **19 Domain Events**: Historical facts
- **51+ Handlers**: Command, query, event handlers with @handles decorator
- **3 App Services**: MessageOrchestrationService, AIResponseCoordinator, ChatNotificationService
- **UnitOfWork**: Transaction management

**Key Concept:** Handlers are dependency-injected with repositories and domain services, never directly manipulate DB.

### 3. Domain Layer (`src/domain/`)
**Responsibility:** Pure business logic (ZERO infrastructure dependencies)

- **8 Bounded Contexts**: Meal, Nutrition, User, Meal Planning, Conversation, Notification, AI, Chat
- **30+ Domain Entities**: Rich models with validation
- **50+ Domain Services**: TDEE, nutrition, meal planning, suggestions, translation, notifications
- **6 Analysis Strategies**: Strategy Pattern for flexible meal analysis
- **17 Port Interfaces**: Dependency inversion for repositories and services

**Key Concept:** Domain layer knows nothing about HTTP, databases, or external APIs. It only knows business rules.

### 4. Infrastructure Layer (`src/infra/`)
**Responsibility:** Technical implementation details

- **MySQL + SQLAlchemy 2.0**: 13+ tables, connection pooling (20 + 10 overflow)
- **Alembic Migrations**: Database version control
- **10+ Repositories**: Smart sync, eager loading, request-scoped sessions
- **Redis Cache**: Cache-aside pattern, graceful degradation
- **PyMediator Event Bus**: Singleton registry, async handler execution
- **External Services**: Firebase FCM, Cloudinary, Gemini, Pinecone, RevenueCat, Sentry
- **WebSocket**: ConnectionManager for real-time connections

---

## Key Architectural Patterns

### Dependency Inversion

Domain layer defines ports (interfaces); infrastructure implements them.

```
Domain (defines interface)
    ↓
Infrastructure (implements interface)
    ↓
Handler (depends on abstraction, not concrete impl)
```

### CQRS (Command Query Responsibility Segregation)

Separates write (commands) from read (queries) operations:

- **Commands**: CreateMealCommand, UpdateUserMetricsCommand (execute business logic, publish events)
- **Queries**: GetMealByIdQuery, SearchFoodsQuery (read-only, return immediately)
- **Events**: MealCreatedEvent, UserOnboardedEvent (fire-and-forget, processed async)

See `docs/cqrs-guide.md` for detailed patterns.

### Event Bus (PyMediator)

Singleton registry pattern prevents memory leaks:

```python
# Commands/Queries (synchronous)
result = await event_bus.send(CreateMealCommand(...))

# Events (asynchronous, fire-and-forget)
await event_bus.publish(MealCreatedEvent(...))
```

### Repository Pattern

Repositories encapsulate data access with smart sync and eager loading:

```python
def save(self, meal: Meal) -> Meal:
    # Smart sync: update existing or create new
    # Diff-based updates for nested entities
    pass

def find_by_id(self, meal_id: str) -> Optional[Meal]:
    # Eager loading with joinedload
    # Convert DB model to domain entity
    pass
```

---

## Bounded Contexts (Domain)

| Context | Purpose | Key Entities |
|---------|---------|--------------|
| Meal | Core meal operations | Meal (state machine), MealImage, Ingredient |
| Nutrition | Macro/micro data | Nutrition, FoodItem, Macros, Micros |
| User | User profiles & metrics | User, UserProfile, Activity, TdeeRequest |
| Meal Planning | Weekly/daily plans | MealPlan, PlannedMeal, DayPlan, UserPreferences |
| Conversation | Chat state | Conversation, Message, ConversationState |
| Notification | Push notifications | UserFcmToken, NotificationPreferences, PushNotification |
| AI | AI response models | GPTAnalysisResponse, GPTFoodItem, GPTResponseError |
| Chat | Real-time messaging | Thread, Message, ThreadStatus, MessageRole |

---

## Data Flow Example: Meal Analysis

1. API POST `/v1/meals/image/analyze` receives image
2. Route creates `UploadMealImageImmediatelyCommand`
3. EventBus.send() → `UploadMealImageImmediatelyCommandHandler`
4. Handler uploads image to Cloudinary, creates Meal with PROCESSING status, publishes `MealImageUploadedEvent`
5. EventBus.publish() → `MealAnalysisEventHandler` (background)
6. Background handler calls `VisionAIService` (Gemini), parses nutrition, updates Meal to READY
7. Handler returns Meal to API layer immediately (step 4)

**Result:** Synchronous response to client, async analysis in background.

---

## Architectural Strengths

1. **Clear Separation of Concerns**: 4 distinct layers
2. **CQRS Flexibility**: Independent scaling of reads/writes
3. **Event-Driven Scalability**: Async background processing
4. **Dependency Inversion**: Domain has zero infrastructure dependencies
5. **Testability**: 681+ tests, 70%+ coverage (isolated handlers, injected deps)
6. **Graceful Degradation**: Cache/service failures handled gracefully

---

## Known Issues

1. CORS wide open in production (`allow_origins=["*"]`)
2. Premium features not restricted on routes
3. No API versioning strategy (only v1)
4. Hardcoded constants not in config
5. CloudinaryImageStore created directly in routes (not DI)

---

See related: `cqrs-guide.md`, `database-guide.md`, `external-services.md`, `code-standards.md`
