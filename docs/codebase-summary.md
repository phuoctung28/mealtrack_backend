# Backend Codebase Summary

**Generated:** May 27, 2026
**Status:** Production-ready (430 files, ~38.5K LOC, 681+ tests, 70%+ coverage)
**Language:** Python 3.11+ | **Framework:** FastAPI 0.115+ + SQLAlchemy 2.0

---

## Codebase Metrics

| Metric | Value |
|--------|-------|
| Total Source Files | 430 Python files |
| API Layer | 76 files, ~8,605 LOC |
| Application Layer | 140 files, ~6,229 LOC |
| Domain Layer | 133 files, ~14,556 LOC |
| Infrastructure Layer | 80 files, ~8,895 LOC |
| Total LOC (src/) | ~38,300 LOC |
| Test Files | 92 files |
| Total Test Cases | 681+ tests |
| Test Coverage | 70%+ maintained |
| API Endpoints | 60+ REST endpoints across 17 route modules |
| CQRS Commands | 30 commands across 11 domains |
| CQRS Queries | 31 query definitions |
| Domain Events | 19 event definitions |
| Handlers | 51 handlers with @handles decorator (28+ cmd, 24+ query, 1 event) |
| Application Services | 3 (MessageOrchestrationService, AIResponseCoordinator, ChatNotificationService) |
| Domain Services | 50+ service files |
| Bounded Contexts | 8 contexts (Meal, Nutrition, User, Planning, Conversation, Notification, AI, Chat) |
| Analysis Strategies | 6 strategies (basic, portion, ingredient, weight, user-context, combined) |
| Database Tables | 13+ (core + notification_sent_log for dedup) |
| Repositories | 10+ with smart sync and eager loading |
| Port Interfaces | 17 port interfaces for dependency inversion |
| External Integrations | 9 (Gemini, Pinecone, Firebase, Cloudinary, RevenueCat, PostHog, Redis, MySQL, Sentry) |

---

## Key Directories

| Directory | Files | Purpose |
|-----------|-------|---------|
| `src/api/routes/v1/` | 17 | 60+ REST endpoints |
| `src/api/schemas/` | 34 | Pydantic DTOs |
| `src/app/commands/` | 30 | Write operations |
| `src/app/queries/` | 31 | Read operations |
| `src/app/handlers/` | 51+ | CQRS handlers |
| `src/domain/model/` | 44 | Domain entities (8 bounded contexts) |
| `src/domain/services/` | 50+ | Domain services |
| `src/infra/database/models/` | 13+ | Database tables |
| `src/infra/repositories/` | 10+ | Data access |
| `src/infra/services/` | 8+ | External services |
| `tests/` | 92 | 681+ tests (70%+ coverage) |

---

## Recent Features (May 2026)

- **Notification / Push Overhaul:** Platform-specific payload builders (`src/infra/services/push/`); Android high-priority FCM, APNs Time Sensitive with `interruption-level` in payload body; trial-expiry pushes at T-2d and T-1d; notifications rescheduled on timezone changes; `SchedulerLeaderLock` (flock + PostgreSQL advisory lock) for multi-replica deployments; `DailyContextPrecomputeService` pre-computes calorie context at timezone midnight
- **RevenueCat Webhook Expansion:** Full lifecycle coverage (INITIAL_PURCHASE, RENEWAL, CANCELLATION, EXPIRATION, BILLING_ISSUE, PRODUCT_CHANGE, REFUND, TRANSFER); referral credit/revoke on purchase/refund; PostHog lifecycle mirroring
- **PostHog Analytics Adapter:** `src/infra/adapters/posthog_adapter.py` — fire-and-forget async capture; enabled by `POSTHOG_API_KEY`
- **Parallel Recipe Generator:** `src/domain/services/meal_suggestion/parallel_recipe_generator.py` with per-recipe attempt logic in `recipe_attempt_builder.py`; 3-phase pipeline: name generation → parallel recipe generation → translation
- **Scheduled Email Service:** `ScheduledEmailService` runs re-engagement and trial-expiry emails at startup via `src/infra/services/scheduled_email_service.py`
- **Configurable Referral Commission:** `REFERRAL_COMMISSIONS` env var (JSON dict, per-currency, default 2 USD)
- **Variable-Length Referral Codes:** 3–15 character codes

---

## Entry Points

- **FastAPI app:** `src/api/main.py`
- **CLI**: `python -m src.api.main` or `uvicorn src.api.main:app --reload`
- **Tests:** `pytest` or `pytest -m unit`
- **Migrations:** `alembic upgrade head` or `alembic revision --autogenerate -m "..."`

---

## Core Domain Services

| Service | Purpose |
|---------|---------|
| TdeeCalculationService | TDEE + macro calculations (auto-formula selection) |
| MealCoreService | Meal lifecycle & state machine |
| NutritionCalculationService | Nutrition aggregation from food items |
| SuggestionOrchestrationService | Session-based meal suggestions (4h Redis TTL) |
| MealGenerationService | Multi-model Gemini for meal generation |
| TranslationService | 7-language support (en, vi, es, fr, de, ja, zh) |
| NotificationService | FCM push notifications with dedup; platform-specific builders; scheduler leader election |
| MealDiscoveryService | Image-based meal discovery |

---

See detailed docs: `system-architecture.md`, `cqrs-guide.md`, `database-guide.md`, `external-services.md`
