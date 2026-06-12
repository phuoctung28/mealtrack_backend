# Backend System Architecture Overview

**Last Updated:** June 12, 2026
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
| Infra | 80 | ~8,895 | 13+ DB tables, 10+ repos, Redis, PyMediator, external adapters, push payload builders |
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

Background subscriber tasks are owned by `BackgroundTaskManager` (`src/infra/event_bus/background_task_manager.py`), which replaces bare `asyncio.create_task` in the event bus and routes; it exposes `spawn`, `drain`, and `shutdown` so subscriber failures are observable and app shutdown can cancel outstanding tasks cleanly.

### Repository Pattern
Async SQLAlchemy repositories are accessed through `AsyncUnitOfWork`. The UoW owns commit/rollback boundaries; repositories flush only when generated IDs or relationship state are needed.

---

## Bounded Contexts (Domain)

| Context | Key Entities |
|---------|-------------|
| Meal | Meal (state machine), MealImage, Ingredient |
| Nutrition | Nutrition, FoodItem, Macros, Micros |
| User | User, UserProfile, Activity, TdeeRequest |
| Meal Planning | MealPlan, PlannedMeal, DayPlan, UserPreferences |
| Conversation | Conversation, Message, ConversationState |
| Notification | UserFcmToken, NotificationPreferences, PushNotification, NotificationSentLog |
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

## Affiliate System Boundary

MealTrack and nutree-affiliate are **separate services with separate databases**. MealTrack must never join against or directly write affiliate tables.

```
Nutree mobile ──→ MealTrack (validate/apply code)
                       │
                       │ same DB transaction
                       ▼
               affiliate_event_outbox
                       │
                       │ cron every 5 min
                       ▼
              nutree-affiliate API  ──→ nutree-affiliate DB
                 (Vercel)              (commission ledger, payout)
```

**Identity separation:** A nutree app user and an affiliate user are distinct identities even when their email addresses match. MealTrack holds only `mealtrack_user_id`; nutree-affiliate holds only `affiliate_id`.

**Ownership rules:**

| Data | Owner |
|------|-------|
| App users, subscriptions, RevenueCat events | MealTrack |
| Affiliate identity, codes, commission rules | nutree-affiliate |
| Ledger credits/reversals, payout state | nutree-affiliate |
| `affiliate_event_outbox` retry queue | MealTrack (infrastructure only) |

**Integration:** See `docs/external-services.md` → nutree-affiliate section.

---

## Current Alignment And Backlog

- Database runtime is async-only: request paths, cron jobs, and handlers use
  `config_async.py`, `AsyncSession`, `AsyncUnitOfWork`, and async repositories.
  Alembic uses its separate migration engine.
- `AsyncUnitOfWork` uses `asyncio.Lock`; concurrent reuse within one instance
  will block by design. The event bus clones stateful handlers so every send
  gets a fresh UoW instance.
- Manual meal save (`POST /v1/meals/manual`) instruments `db_ms` and `cache_ms`
  in structured logs so DB commit and Redis cache invalidation latency are
  independently observable without logging food payload or auth data.
- Future features must follow
  `docs/architecture/async-cqrs-feature-alignment.md`.
- Alignment backlog: move shared exceptions out of `src/api`, shrink
  import-linter baselines, route new feature writes through CQRS handlers and
  UoW-owned repositories, make long-lived background refresh loops use the
  process task manager, and expand static guards for sync `httpx` calls.

---

See related: `cqrs-guide.md`, `database-guide.md`, `external-services.md`,
`code-standards.md`, `architecture/async-cqrs-feature-alignment.md`
