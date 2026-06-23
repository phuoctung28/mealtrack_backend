# Backend Codebase Summary

**Generated:** June 22, 2026
**Status:** Production-ready snapshot of the live backend codebase
**Runtime:** FastAPI 0.115+ on Python 3.11+ with async SQLAlchemy 2.0

---

## Codebase Metrics

| Metric | Value |
|--------|-------|
| Source files | 620 Python files in `src/` |
| Source LOC | ~52.6K LOC in `src/` |
| Test files | 291 Python files in `tests/` |
| Collected tests | 1,600+ collected tests |
| API routers | 26 router registrations in `src/api/main.py` |
| API endpoints | 83 endpoint decorators under `src/api/routes/` |
| CQRS command files | 51 |
| CQRS query files | 50 |
| CQRS event files | 15 |
| CQRS handler files | 87 |
| Domain service files | 50 |
| Port files | 26 |
| Database model files | 47 |
| ORM table declarations | 36 |

---

## Layer Snapshot

| Layer | Files | LOC | Notes |
|-------|-------|-----|-------|
| API | 89 | ~10.4K | Routes, middleware, schemas, dependency wiring, and API mappers |
| Application | 208 | ~11.0K | Commands, queries, handlers, and orchestration services |
| Domain | 160 | ~15.5K | Entities, services, ports, policies, and bounded contexts |
| Infrastructure | 154 | ~15.0K | Database, cache, adapters, observability, and service integrations |

---

## Live API Surface

The current HTTP surface includes:

- Meal logging and analysis: image upload, upload-token, scan-by-url, manual meals, parse-text, streak, weekly budget, and daily macros.
- User and profile management: Firebase sync, onboarding completion, metrics, TDEE, language, timezone, and account deletion.
- Discovery and planning: meal suggestions discover, recipes, and save.
- Nutrition and activity tracking: nutrition bulk/presence, activities daily/bulk, hydration, movement, and the journey progress snapshot.
- Support routes: foods, ingredients, notifications, feature flags, saved suggestions, cheat days, referrals, promo codes, unified code validation, monitoring, health, app download, and well-known links.

---

## Core Runtime Notes

- Runtime DB access uses PostgreSQL/Neon via `src/infra/database/config_async.py` and `asyncpg`.
- Redis is optional and used for cache-aside and AI-context caching, not as the source of truth.
- Database migrations are Alembic-managed and run before app startup through the entrypoint/pre-deploy flow.
- The event bus is a singleton PyMediator registry wired from `src/api/dependencies/event_bus.py`.

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

## Recent Features (June 2026)

- **Canonical AI Nutrition Contracts + Validation Retry:** `src/domain/model/ai/nutrition_contracts.py` defines image and text nutrition contracts with bounded food counts, strict quantity validation, and backend-calorie authority; invalid structured meal image/text output now retries exactly once before a controlled `AIOutputValidationError`, while ingredient recognition keeps its unstructured `{name, confidence, category}` contract and the legacy parser no longer silently drops invalid AI food items.
- **Notification / Push Overhaul:** Platform-specific payload builders (`src/infra/services/push/`); Android high-priority FCM, APNs Time Sensitive with `interruption-level` in payload body; trial-expiry pushes at T-2d and T-1d; notifications rescheduled on timezone changes; cron push (`src/cron/push.py`) precomputes notification rows, schedules trial-expiry rows, dispatches due rows through database row claiming, and cleans expired rows
- **RevenueCat Webhook Expansion:** Full lifecycle coverage (INITIAL_PURCHASE, RENEWAL, CANCELLATION, EXPIRATION, BILLING_ISSUE, PRODUCT_CHANGE, REFUND, TRANSFER); referral credit/revoke on purchase/refund; PostHog lifecycle mirroring
- **PostHog Analytics Adapter:** `src/infra/adapters/posthog_adapter.py` — fire-and-forget async capture; enabled by `POSTHOG_API_KEY`
- **Parallel Recipe Generator:** `src/domain/services/meal_suggestion/parallel_recipe_generator.py` with per-recipe attempt logic in `recipe_attempt_builder.py`; 3-phase pipeline: name generation → parallel recipe generation → translation
- **Cron Lifecycle Email Service:** `src/cron/email.py` runs re-engagement and trial-expiry lifecycle emails via `CronLifecycleEmailService`
- **Configurable Referral Commission:** `REFERRAL_COMMISSIONS` env var (JSON dict, per-currency, default 2 USD)
- **Variable-Length Referral Codes:** 3–15 character codes
- **AI Handshake Guest Trial Quota (Postgres):** `src/api/services/guest_parse_quota.py` + table `ai_handshake_guest_trial_quotas`; enforces one-shot AI trial per guest install HMAC hash using Postgres row-level locking (INSERT+conflict → SELECT FOR UPDATE); Redis not required for this endpoint.

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
| MealDiscoveryService | Image-based meal discovery |

---

See detailed docs: `system-architecture.md`, `cqrs-guide.md`, `database-guide.md`, `external-services.md`
