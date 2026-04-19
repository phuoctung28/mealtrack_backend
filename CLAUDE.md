# Backend — FastAPI

Monorepo submodule. 4-layer Clean + CQRS + PyMediator event bus.

## Quick Reference

| Item | Value |
|------|-------|
| **Framework** | FastAPI 0.115+ / Python 3.11+ |
| **Database** | MySQL 8.0 + SQLAlchemy 2.0 |
| **Migrations** | Alembic |
| **Event Bus** | PyMediator (singleton) |
| **AI** | Google Gemini (multi-model) |
| **Auth** | Firebase JWT |
| **Cache** | Redis (cache-aside) |

## Critical Commands (Daily Use)

```bash
# Development
uvicorn src.api.main:app --reload

# Database
alembic upgrade head
alembic revision --autogenerate -m "description"

# Code quality (run before commit)
black src/ tests/ && flake8 src/ && mypy src/ && pytest
```

## MUST-Follow Rules (Non-Inferable)

**Architecture**: 4-layer Clean + CQRS (see `docs/system-architecture.md`)
- API layer → Application layer (commands/queries)
- Application layer → Domain layer (services)
- Domain layer has ZERO external dependencies

**Event Bus**: PyMediator with singleton registry pattern (see `docs/cqrs-guide.md`)
- Commands emit events (don't return data)
- Queries return immediately
- Events processed asynchronously

**Calories = Derived from Macros** (non-negotiable)
- Backend is source of truth: `P*4 + (C-fiber)*4 + fiber*2 + F*9`
- Mobile receives all calorie values from backend
- Never re-derive on mobile

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
