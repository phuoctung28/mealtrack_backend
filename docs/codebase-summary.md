# Backend Codebase Summary

**Generated:** July 29, 2026
**Status:** Current snapshot of the live backend codebase
**Runtime:** FastAPI 0.136.3 on Python 3.13.2 with async SQLAlchemy 2.0

---

## Codebase Metrics

| Metric | Value |
|--------|-------|
| Source files | 704 Python files in `src/` |
| Source LOC | 65,423 LOC in `src/` |
| Test files | 350 Python files in `tests/` |
| Collected tests | 2,013 unit tests in `tests/unit`; broad unscoped collection still hits two duplicate-package import collisions |
| Route files | 31 route files total; 28 endpoint-bearing modules |
| Router registrations | 29 `include_router(...)` calls in `main.py` |
| Endpoint decorators | 98 standard `@router` verb handlers plus 2 health `api_route` declarations |

---

## Layer Snapshot

| Layer | Files | LOC | Notes |
|-------|-------|-----|-------|
| API | 97 | 12,709 | Routes, middleware, schemas, dependency wiring, and API mappers |
| Application | 244 | 14,684 | CQRS commands, queries, handlers, and orchestration services |
| Domain | 192 | 19,522 | Entities, services, ports, policies, and bounded contexts |
| Infrastructure | 162 | 17,762 | Database, cache, adapters, observability, and service integrations |
| **Total** | **695** | **64,677** | Layer directories only; the remaining `src/` files are root/bootstrap/cron modules |

---

## Live API Surface

The current HTTP surface includes:

- Meal logging and analysis: image upload, upload-token, scan-by-url, food-label scan-by-url, manual meals, parse-text, streak, weekly budget, and daily macros.
- Meal recommendations: durable three-day catalog plans, compact summaries, slot detail hydration, and swap/log/skip mutations.
- User and profile management: Firebase sync, onboarding completion, metrics, TDEE, language, timezone, and account deletion.
- Discovery and planning: meal suggestions discover, recipes, and save.
- Nutrition and activity tracking: nutrition bulk/presence, activities daily/bulk, hydration, movement, and the journey progress snapshot.
- Support routes: foods, ingredients, notifications, feature flags, saved suggestions, cheat days, referrals, promo codes, unified code validation, monitoring, health, app download, and well-known links.

---

## Core Runtime Notes

- Runtime DB access uses PostgreSQL/Neon via `src/infra/database/config_async.py` and async SQLAlchemy.
- Redis is optional for cache-aside and AI-context caching; required state is modeled separately.
- The active meal-image-name vector cache uses `pgvector`; Pinecone is legacy documentation only and has no runtime adapter.
- OpenAI is the default AI provider. Cloudflare Workers AI is available for configured text and vision purposes. Gemini packages remain in dependencies, but the runtime provider registry is OpenAI + Cloudflare.
- Database migrations live in `migrations/versions/` and are applied with Alembic.
- The event bus is a singleton PyMediator registry wired from `src/api/dependencies/event_bus.py`.

---

## Key Directories

| Directory | Files | Purpose |
|-----------|-------|---------|
| `src/api/routes/v1/` | 28 | Versioned REST route modules |
| `src/api/schemas/` | 37 | Pydantic DTOs |
| `src/app/commands/` | 57 | Write-operation command packages |
| `src/app/queries/` | 56 | Read-operation query packages |
| `src/app/handlers/` | 96 | CQRS handlers and support modules |
| `src/domain/model/` | 66 | Domain entities and value objects |
| `src/domain/services/` | 70 | Domain services and policies |
| `src/infra/database/models/` | 51 | ORM model packages and table declarations |
| `src/infra/repositories/` | 26 | Data access adapters |
| `src/infra/services/` | 27 | Infrastructure services and AI providers |
| `tests/` | 350 | Unit, architecture, migration, and explicit integration tests |

---

## Recent Characterization Work

- **Meal recommendation contract refresh:** `/v1/meal-recommendations/three-day` and `GET /v1/meal-recommendations/{plan_id}` return compact selected-slot summaries; slot detail hydrates one selected slot plus alternatives; swap/log/skip return changed-slot detail responses.
- **Food-label scan:** `/v1/meals/food-label/scan-by-url` analyzes Cloudinary nutrition-label images directly and persists only validated READY meals.
- **Hydration API refresh:** `GET /v1/hydration/catalog` exposes the visible drink catalog, while `GET /v1/hydration/daily` and `GET /v1/hydration/weekly` now derive goal, percentage, and streak behavior from the current handlers.

---

## Entry Points

- **FastAPI app:** `src/api/main.py`
- **CLI:** `python -m src.api.main` or `uvicorn src.api.main:app --reload`
- **Tests:** `pytest tests/unit --cov=src --cov-fail-under=65` for the default CI-aligned suite
- **Migrations:** `alembic upgrade head` or `python migrations/run.py` for fresh bootstrap / guarded recovery

---

## Core Domain Services

| Service | Purpose |
|---------|---------|
| TdeeCalculationService | TDEE + macro calculations |
| MealCoreService | Meal lifecycle & state machine |
| NutritionCalculationService | Nutrition aggregation from food items |
| SuggestionOrchestrationService | Session-based meal suggestions |
| MealRecommendation ranking services | Deterministic catalog-backed three-day recommendations |
| TranslationService | 7-language support (en, vi, es, fr, de, ja, zh) |
| MealDiscoveryService | Image-based meal discovery |

---

See detailed docs: `system-architecture.md`, `cqrs-guide.md`, `database-guide.md`, `external-services.md`
