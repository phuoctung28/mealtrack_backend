# Backend System Architecture Overview

**Last Updated:** June 22, 2026
**Architecture:** 4-Layer Clean + CQRS + Event-Driven
**Event Bus:** PyMediator (singleton registry pattern)
**Codebase:** 620 Python files, ~52.6K LOC in `src/`

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (89 files)                    │
│  HTTP Routing │ Pydantic Validation │ Auth │ Middleware      │
└────────────────────────┬────────────────────────────────────┘
                         │ Commands/Queries
┌────────────────────────▼────────────────────────────────────┐
│              Application Layer (208 files)                   │
│  CQRS Handlers │ Event Publishing │ App Services             │
└────────────────────────┬────────────────────────────────────┘
                         │ Domain Services
┌────────────────────────▼────────────────────────────────────┐
│                Domain Layer (160 files)                      │
│  Business Logic │ Domain Models │ Port Interfaces            │
└────────────────────────┬────────────────────────────────────┘
                         │ Port Implementations
┌────────────────────────▼────────────────────────────────────┐
│            Infrastructure Layer (154 files)                  │
│  DB │ Cache │ External APIs │ Event Bus │ Config             │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer Statistics

| Layer | Files | LOC | Key Contents |
|-------|-------|-----|-------------|
| API | 89 | ~10,361 | 26 router registrations, 83 endpoint decorators, schemas, middleware, dependencies |
| App | 208 | ~10,984 | 51 command files, 50 query files, 15 event files, 87 handler files |
| Domain | 160 | ~15,460 | Meal, nutrition, user, hydration, movement, progress, notification, planning, referral-facing policies |
| Infra | 154 | ~15,041 | PostgreSQL/pgvector, Redis, PyMediator, external adapters, observability, push/email services |
| **Total** | **611** | **~51,846** | Layer directories only; `src/` also has bootstrap, cron, and observability modules |

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

### Observability Connector
Observability uses a provider-neutral facade at `src.observability` so API middleware does not import infrastructure directly. Infrastructure owns the Sentry connector, and startup composition wires it through `src.bootstrap.observability`. The compatibility export at `src.infra.monitoring` remains for cron and infrastructure services. Direct `sentry_sdk` imports are isolated to `src/infra/monitoring/sentry.py`.

The connector sends unexpected API failures, `ERROR` logs, sampled request/SQL/cron spans, explicit Sentry Logs, operational metrics, swallowed cron failures, and affiliate outbox permanent failures. It does not send expected 4xx/business errors, product analytics, request bodies, auth headers, Firebase claims, emails, food payloads, raw image URLs, provider payloads, or secrets. Context, log attributes, and metric attributes are allowlisted scalar values.

### Exception Ownership by Layer (Single-Owner Logger)

**Rule: log-or-raise, not both.** One root-cause `ERROR` per unexpected request failure.

| Layer / File | Role | Log behavior |
|---|---|---|
| `src/api/exception_handlers.py` | Global FastAPI boundary | Owns single `ERROR` for unexpected exceptions; `MealTrackException` converts silently (no log); `AIUnavailableError` logs `WARNING` |
| `src/api/middleware/request_logger.py` | Outcome indicator | 5xx response lines logged at `WARNING` — never `ERROR`; root-cause ERROR is upstream |
| Command/query handlers | Pure conversion | Call `handle_exception()` or propagate directly; do **not** log before re-raising |
| Event handlers / background tasks | Swallowing boundary | Own their `ERROR` log + `capture_exception` at subscriber boundary |
| `src/cron/email.py`, `src/cron/push.py` | Cron boundary | `capture_exception` + `flush_observability` on failure; `log_event("info", "cron.phase.completed")` per phase |

Architecture guardrails enforced by `tests/unit/architecture/test_logging_ownership_guardrails.py`: bans direct `sentry_sdk` outside connector, log-and-rethrow pattern, and sensitive substrings in log statements.

---

## Bounded Contexts (Domain)

| Context | Key Entities |
|---------|-------------|
| Meal | Meal (state machine), MealImage, Ingredient, image cache projection |
| Nutrition | Nutrition, FoodItem, Macros, Micros |
| User | User, UserProfile, Activity, TdeeRequest, weight history |
| Hydration | Hydration entries, drink catalog, caloric drink logging |
| Movement | Movement entries, activity catalog, daily movement summaries |
| Progress | Journey progress snapshot, active-period filtering, action scoring |
| Meal Planning | Weekly budget, meal planning, meal suggestion, saved suggestion models |
| Notification | UserFcmToken, NotificationPreferences, PushNotification, queued notification rows |
| AI | GPTAnalysisResponse, GPTFoodItem, GPTResponseError |
| Commerce | Subscription state, referral code application, promo code redemption |

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

## Known Issues

- Premium features not restricted on routes (`require_premium` dependency not applied)
- No API versioning strategy beyond v1
- `CloudinaryImageStore` instantiated directly in routes (not via DI)
- Hardcoded constants (MAX_FILE_SIZE, SLOW_REQUEST_THRESHOLD) not in config
- CORS is configured only when `ALLOWED_ORIGINS` is set; production origin values still need deployment review.
- `AsyncUnitOfWork` uses `asyncio.Lock`; concurrent reuse within one instance will block (by design — use separate instances per handler, enforced by event bus handler cloning)
- Database runtime is async-only: request paths, cron jobs, and handlers use `config_async.py`, `AsyncSession`, `AsyncUnitOfWork`, and async repositories. Alembic uses its separate migration engine.
- Manual meal save (`POST /v1/meals/manual`) instruments `db_ms` and `cache_ms` in structured logs so DB commit and Redis cache invalidation latency are independently observable without logging food payload or auth data.

---

See related: `cqrs-guide.md`, `database-guide.md`, `external-services.md`, `code-standards.md`
