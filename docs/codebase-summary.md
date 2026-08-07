# Backend Codebase Summary

**Last Updated:** August 7, 2026
**Status:** Navigation snapshot — discover live counts from the tree and OpenAPI, not this file
**Runtime:** FastAPI 0.136.3 on Python 3.13.2 with async SQLAlchemy 2.0

---

## How to discover inventory

| Need | Owner |
|------|-------|
| Live HTTP surface | `/docs` (Swagger) and `src/api/main.py` router registrations |
| Layer layout | `src/api/`, `src/app/`, `src/domain/`, `src/infra/` plus root/bootstrap/cron |
| Tests | `pytest tests/unit --cov=src --cov-fail-under=65` (default CI path) |
| Migrations | `migrations/versions/` via Alembic |

Do not hand-maintain file, LOC, or endpoint counts in this document.

---

## Live API Surface

The current HTTP surface includes:

- Meal logging and analysis: image upload, upload-token, scan-by-url, food-label scan-by-url, manual meals, parse-text, ingredient edits with optional nutrition overrides, streak, weekly budget, and daily macros.
- Meal recommendations: durable three-day catalog plans, compact summaries (including selected ingredients), slot detail hydration, and swap/log/skip mutations.
- Paid web redemption: `/v1/web-funnel/*` lead, RevenueCat correlation, passwordless preflight, and finalize routes.
- User and profile management: Firebase sync, onboarding completion, metrics, TDEE, language, timezone, and account deletion.

Onboarding TDEE preview is versioned as `onboarding_preview_v2`; the backend
owns activity/motivation calculation, Keto 5/20/75 policy, and macro-derived
calories. No-training is `(0, 0)` with `(0, 15)` retained for legacy clients.
Preview bodies are capped at 8 KiB before parsing and subject to IP quota;
custom macro triples, reset, and target/cache revisions are fenced against
stale writes. Body-fat projections are illustrative/source-guarded, and the
related migration exists but is not applied or deployed.
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

| Directory | Purpose |
|-----------|---------|
| `src/api/routes/v1/` | Versioned REST route modules |
| `src/api/schemas/` | Pydantic DTOs |
| `src/app/commands/` | Write-operation command packages |
| `src/app/queries/` | Read-operation query packages |
| `src/app/handlers/` | CQRS handlers and support modules |
| `src/domain/model/` | Domain entities and value objects |
| `src/domain/services/` | Domain services and policies |
| `src/infra/database/models/` | ORM model packages and table declarations |
| `src/infra/repositories/` | Data access adapters |
| `src/infra/services/` | Infrastructure services and AI providers |
| `tests/` | Unit, architecture, migration, and explicit integration tests |

---

## Recent Characterization Work

- **Manual nutrition overrides:** meal and ingredient edit requests can store absolute override macros/calories while preserving source nutrition for clear/restore.
- **Paid web redemption:** RevenueCat web checkout correlates by redemption-link hash, preflights after Firebase passwordless email-link sign-in, and finalizes against provider aliases.
- **Meal recommendation contract:** compact selected-slot summaries include ingredients; slot detail hydrates alternatives; swap/log/skip return changed-slot detail responses.
- **Food-label scan:** `/v1/meals/food-label/scan-by-url` analyzes Cloudinary nutrition-label images directly and persists only validated READY meals.
- **Hydration API:** catalog, daily, and weekly handlers own goal, percentage, and streak presentation.

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
