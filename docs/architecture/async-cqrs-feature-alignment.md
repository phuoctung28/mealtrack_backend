# Async CQRS Feature Alignment

**Last verified:** 2026-06-12
**Scope:** Future backend features in `src/api`, `src/app`, `src/domain`, and `src/infra`.

## Purpose

Every new backend feature should follow the same runtime path:

```text
FastAPI route -> command/query -> handler -> domain service/port -> infra adapter/repository
```

The backend runtime is already async. Do not treat old file names or the
presence of migration-only sync tooling as proof that the request path is sync.
Use the verified runtime files below as the source of truth.

## Current Runtime Baseline

| Area | Current source of truth |
|---|---|
| App DB engine | `src/infra/database/config_async.py` |
| DB mode policy | `src/infra/database/connection_policy.py` |
| Transaction boundary | `src/infra/database/uow_async.py` |
| CQRS composition root | `src/api/dependencies/event_bus.py` |
| Event dispatch | `src/infra/event_bus/pymediator_event_bus.py` |
| Background task owner | `src/infra/event_bus/background_task_manager.py` and `src/api/dependencies/task_manager.py` |
| Static async guardrails | `tests/architecture/test_async_boundary_hygiene.py` |
| Async DB/runtime guardrails | `tests/architecture/test_async_db_runtime_boundaries.py` |
| Layer import contracts | `.importlinter` |

Validated on 2026-06-12:

- `pytest tests/architecture/test_async_boundary_hygiene.py tests/architecture/test_async_db_runtime_boundaries.py -q`
- `lint-imports`

## New Feature Rules

### API Layer

- Routes parse HTTP input, auth, timezone, language, files, and Pydantic DTOs.
- Routes send commands or queries through the configured event bus.
- Routes do not call `commit()`, `rollback()`, or mutate DB-owned state directly.
- Routes map application errors to HTTP responses; lower layers should not import
  `fastapi.HTTPException`.

### Application Layer

- Writes are commands. Reads are queries. Both are async.
- Handlers own orchestration and call domain services or repository ports.
- Handlers use `AsyncUnitOfWork` or an injected `AsyncUnitOfWorkPort` for DB work.
- Do not add new direct app-to-infra imports. Existing `.importlinter`
  allowlists are debt to shrink, not examples to copy.
- Do not call `uow.session.commit()` directly. Use the UoW context manager or
  `await uow.commit()` where explicit early commit is required.

### Domain Layer

- Domain code stays framework-free and infrastructure-free.
- Domain services may coordinate pure business logic and domain ports.
- Domain must not import `src.api`, `src.app`, `src.infra`, `sqlalchemy`,
  `httpx`, `redis`, or Firebase SDKs.
- Calories remain backend-owned and derived from macros:
  `protein*4 + (carbs-fiber)*4 + fiber*2 + fat*9`.

### Infrastructure Layer

- Repositories use `AsyncSession` and never own transaction commits.
- Repositories may `flush()` when IDs or relationship state are needed.
- External HTTP clients on async paths use `httpx.AsyncClient`.
- Sync vendor SDKs are allowed only behind explicit `asyncio.to_thread(...)`
  wrappers or another documented off-loop boundary.
- Required state is not cache. Optional Redis cache must pass the selective
  admission policy in `docs/decisions/260608-2223-selective-cache-admission-policy.md`.

### Events And Background Work

- Event handlers are fire-and-forget only when side effects are non-critical or
  retriable elsewhere.
- Background tasks must be awaited, supervised by `BackgroundTaskManager`, or
  moved to durable DB-backed work.
- Do not introduce bare `asyncio.create_task(...)` in routes or event-bus code.
- Parallel in-request work may use tasks only when all tasks are awaited with
  `gather`, `as_completed`, or equivalent cleanup.

### Connection Pool Policy

- Default production mode is `DB_CONNECTION_MODE=direct_pool` with a direct Neon
  URL in `APP_DATABASE_URL` or `DATABASE_URL`.
- App runtime does not read `DATABASE_URL_DIRECT`; that variable is reserved for
  Alembic and migration tooling.
- Direct mode capacity:

```text
total_connections = UVICORN_WORKERS * ASYNC_POOL_SIZE_PER_WORKER + ASYNC_POOL_MAX_OVERFLOW
```

- Starting point previously validated for two workers:
  `ASYNC_POOL_SIZE_PER_WORKER=2`, `ASYNC_POOL_MAX_OVERFLOW=2`,
  `ASYNC_POOL_TIMEOUT=45`, `ASYNC_POOL_RECYCLE=120`.
- `neon_pooler` mode is allowed only with a Neon `-pooler` URL and PgBouncer-safe
  prepared statement settings.

## Security And Trust Boundaries

Security-sensitive future features must explicitly document:

- User ownership boundary: every user-owned read/write must prove `user_id`.
- Auth boundary: Firebase JWT and dev-auth bypass must never share production
  behavior.
- Admin boundary: no broad admin-gate rollout is planned here. If a touched
  feature is already operator-only or creates a new operator-only capability,
  keep using the existing admin dependency pattern.
- Entitlement boundary: RevenueCat remains the subscription source of truth. No
  broad premium-guard rollout is planned here; only wire entitlement checks when
  product scope explicitly requires backend enforcement for that feature.
- Webhook boundary: RevenueCat webhook input is externally controlled and must
  verify the configured secret before mutating subscription state.
- Affiliate boundary: MealTrack owns only app-user state and outbox rows;
  nutree-affiliate owns affiliate identity, ledger, commission, and payout state.
- File/image boundary: client-provided URLs or IDs must be scoped to expected
  storage prefixes before server-side fetch or ownership mutation.
- PII boundary: logs must avoid raw food payloads, secrets, tokens, payout
  details, and Firebase credential material.

## Known Alignment Backlog

These are not blockers for every feature, but future work should shrink them:

1. Move the shared `MealTrackException` hierarchy out of `src/api/exceptions.py`
   into an application/domain error package, then leave HTTP conversion in API.
2. Shrink `.importlinter` app-to-infra and infra-to-api allowlists as features
   touch those handlers/services.
3. Move feature-flag writes fully behind app-layer command handlers or an app
   service that depends on ports, not `src.infra.services`.
4. Route new DB access through repositories/ports instead of raw
   `uow.session.execute(...)` unless the query is truly infrastructure-only.
5. Make the Gemini cache refresh loop use the process task manager before
   expanding background refresh loops.
6. Monitor `cache_ms` in manual-save logs; if consistently above 50 ms, batch
   cache invalidation with Redis pipeline/`UNLINK` while preserving correctness.
7. Extend static guards to catch sync `httpx.get/head/post/...` calls on async
   runtime paths, not only `requests` imports.

## Required Gates For Future Features

Run these for architecture-sensitive backend changes:

```bash
.venv/bin/pytest tests/architecture/test_async_boundary_hygiene.py tests/architecture/test_async_db_runtime_boundaries.py -q
.venv/bin/lint-imports
```

Add targeted unit/integration tests for the specific command, query, route,
repository, cache invalidation path, or external adapter touched by the feature.
