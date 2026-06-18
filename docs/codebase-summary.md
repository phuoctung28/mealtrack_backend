# Backend Codebase Summary

**Generated:** June 18, 2026
**Status:** Production-ready snapshot of the live backend codebase
**Runtime:** FastAPI 0.115+ on Python 3.11+ with async SQLAlchemy 2.0

---

## Current Metrics

| Metric | Value |
|--------|-------|
| Source files | 616 Python files in `src/` |
| Source LOC | ~52.5K LOC in `src/` |
| Test files | 294 Python files in `tests/` |
| Collected tests | 1,600+ collected tests |
| API routers | 26 router registrations in `src/api/main.py` |
| API endpoints | 79 endpoint decorators under `src/api/routes/` |
| CQRS command files | 51 |
| CQRS query files | 50 |
| CQRS event files | 15 |
| CQRS handler files | 87 |
| Domain service files | 50 |
| Port files | 27 |
| Database model files | 46 |
| ORM table declarations | 35 |

---

## Layer Snapshot

| Layer | Files | LOC | Notes |
|-------|-------|-----|-------|
| API | 86 | ~10.1K | Routes, middleware, schemas, dependency wiring, and API mappers |
| Application | 208 | ~10.8K | Commands, queries, handlers, and orchestration services |
| Domain | 160 | ~15.5K | Entities, services, ports, policies, and bounded contexts |
| Infrastructure | 153 | ~15.3K | Database, cache, adapters, observability, and service integrations |

---

## Live API Surface

The current HTTP surface includes:

- Meal logging and analysis: image upload, upload-token, scan-by-url, manual meals, parse-text, streak, weekly budget, and daily macros.
- User and profile management: Firebase sync, onboarding completion, metrics, TDEE, language, timezone, and account deletion.
- Discovery and planning: meal suggestions discover, recipes, and save.
- Nutrition and activity tracking: nutrition bulk/presence, activities daily/bulk, hydration, and movement.
- Support routes: foods, ingredients, notifications, saved suggestions, cheat days, referrals, promo codes, unified code validation, monitoring, health, app download, and well-known links.

---

## Core Runtime Notes

- Runtime DB access uses PostgreSQL/Neon via `src/infra/database/config_async.py` and `asyncpg`.
- Redis is optional and used for cache-aside and AI-context caching, not as the source of truth.
- Database migrations are Alembic-managed and run before app startup through the entrypoint/pre-deploy flow.
- The event bus is a singleton PyMediator registry wired from `src/api/dependencies/event_bus.py`.

---

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `src/api/main.py` | FastAPI app bootstrap and router registration |
| `src/api/routes/` | HTTP endpoints and route modules |
| `src/app/` | CQRS commands, queries, and handlers |
| `src/domain/` | Domain logic, services, and ports |
| `src/infra/` | Database, cache, adapters, observability, and external services |
| `tests/` | Unit, integration, architecture, and migration tests |

---

## Verification Sources

- `src/api/main.py`
- `src/api/routes/`
- `src/api/dependencies/event_bus.py`
- `src/infra/database/config_async.py`
- `src/infra/config/settings.py`
- `docker-compose.yml`
- `pyproject.toml`
