# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI backend for MealTrack. 4-layer Clean Architecture + CQRS + PyMediator event bus.

| Item | Value |
|------|-------|
| **Framework** | FastAPI 0.136+ / Python 3.13 |
| **Database** | PostgreSQL (Neon) + SQLAlchemy 2.0 async |
| **Migrations** | Alembic (timestamp naming for new migrations) |
| **Event Bus** | PyMediator (singleton) |
| **AI** | OpenAI default; optional Cloudflare Workers AI for configured text/vision |
| **Auth** | Firebase JWT |
| **Cache** | Redis (cache-aside, optional) |

## Commands

```bash
# Development server
uvicorn src.api.main:app --reload

# Database migrations
alembic upgrade head                              # Apply pending migrations
alembic revision --autogenerate -m "description"  # Generate new migration
alembic downgrade -1                              # Rollback one migration

# Testing
pytest                                    # Run all tests
pytest tests/unit/                        # Unit tests only
pytest tests/integration/                 # Integration tests only
pytest tests/unit/domain/test_tdee.py -v  # Single test file
pytest --cov=src --cov-report=term        # With coverage

# Code quality (run before commit)
black src/ tests/ && ruff check src/ && mypy src/

# Default CI-aligned tests (prefer targeted path; unscoped pytest can hit import collisions)
pytest tests/unit --cov=src --cov-fail-under=65
```

## Architecture (4-Layer Clean + CQRS)

```
src/
├── api/        # HTTP routing, Pydantic schemas, middleware
├── app/        # CQRS: commands/, queries/, handlers/, events/
├── domain/     # Business logic, services, ports (interfaces)
└── infra/      # Database models, repositories, external adapters
```

**Layer rules** (see `docs/system-architecture.md`):
- API → Application (commands/queries) → Domain (services)
- Domain has ZERO external dependencies (uses ports)
- Infrastructure implements ports

**Event Bus**: PyMediator with singleton registry pattern (see `docs/cqrs-guide.md`)
- Commands emit events (don't return data)
- Queries return immediately
- Events processed asynchronously

**Calories = Backend is source of truth** (non-negotiable)
- Default: fiber-aware macro formula `P*4 + max(C-fiber,0)*4 + fiber*2 + F*9`
- Exception: active meal/ingredient `nutrition_override` uses absolute user values until cleared
- Mobile receives all calorie values from backend; never re-derive on mobile

**Weekly Budget remaining_days Includes Today**
- Mon=7, Tue=6, ..., Sun=1
- Display "X days left" = `remaining_days - 1`
- First day check: `remaining_days >= 7`

## Tier-3 References (Load on Demand)

| Topic | File | Lines |
|-------|------|-------|
| System architecture | `docs/system-architecture.md` | <300 |
| CQRS patterns | `docs/cqrs-guide.md` | <200 |
| API endpoints | `docs/api-endpoints.md` | <150 |
| Database schema | `docs/database-guide.md` | <250 |
| External services | `docs/external-services.md` | <150 |
| Code standards | `docs/code-standards.md` | <300 |
| Testing standards | `docs/testing-standards.md` | <250 |
| Troubleshooting | `docs/troubleshooting.md` | <100 |
