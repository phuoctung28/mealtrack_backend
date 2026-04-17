# Backend Codebase Summary

**Generated:** April 17, 2026  
**Status:** Production-ready (430 files, ~38.5K LOC, 681+ tests, 70%+ coverage)  
**Language:** Python 3.11+ | **Framework:** FastAPI 0.115+ + SQLAlchemy 2.0

---

## Quick Stats

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
| API Endpoints | 50+ REST endpoints across 12 route modules |
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
| External Integrations | 8 (Gemini, Pinecone, Firebase, Cloudinary, RevenueCat, Redis, MySQL, Sentry) |

---

## Key Directories

| Directory | Files | Purpose |
|-----------|-------|---------|
| `src/api/routes/v1/` | 12 | 50+ REST endpoints |
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

## Recent Features (Apr 2026)

- **Sentry Monitoring:** Error tracking, performance monitoring, profiling
- **Meal Discovery:** `/v1/meal-suggestions/discover` with image search (Unsplash/Pexels)
- **Notification Dedup:** Cross-worker FCM deduplication (migration 047)
- **Onboarding Redesign:** Challenge duration, training types (migration 045)
- **Fiber-Aware Calories:** Fiber column + net-carb calorie derivation (migration 034)

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
| NotificationService | FCM push notifications with dedup |
| MealDiscoveryService | Image-based meal discovery |

---

See detailed docs: `system-architecture.md`, `cqrs-guide.md`, `database-guide.md`, `external-services.md`
