---
phase: 1
title: "Connection policy and guardrails"
status: complete
priority: P1
effort: "1-2 days"
dependencies: []
---

# Phase 1: Connection policy and guardrails

## Context Links

- Plan: `./plan.md`
- Research: `./research/runtime-connection-research.md`
- Current runtime: `src/infra/database/config_async.py`
- Current tests: `tests/unit/infra/database/test_config_async.py`

## Overview

Define the app database connection contract before changing behavior. The
deliverable is a small policy layer plus tests that make direct-pool vs
Neon-pooler behavior explicit and fail fast on unsafe env combinations.

## Requirements

- Functional: app runtime URL selection is explicit and testable.
- Functional: pooler mode applies PgBouncer-safe asyncpg settings.
- Functional: direct-pool mode rejects Neon `-pooler` URLs.
- Non-functional: no hidden reliance on `DATABASE_URL_DIRECT` for app runtime.
- Non-functional: migration URL behavior remains direct and sync-engine owned.

## Architecture

Introduce a policy function or small dataclass near database config:

```python
DatabaseConnectionPolicy(
    mode="direct_pool",
    app_url="postgresql+asyncpg://...",
    pool_class="AsyncAdaptedQueuePool",
    connect_args={...},
)
```

Rules:

- `APP_DATABASE_URL` wins for app runtime.
- `DATABASE_URL` is backward-compatible fallback.
- `DATABASE_URL_DIRECT` is migration/admin URL, not silently preferred by app.
- `DB_CONNECTION_MODE=direct_pool` requires a non-`-pooler` host.
- `DB_CONNECTION_MODE=neon_pooler` requires `NullPool` and either
  `prepared_statement_cache_size=0` in URL or equivalent connect/dialect args.

## Related Code Files

- Modify: `src/infra/database/config_async.py`
- Create if needed: `src/infra/database/connection_policy.py`
- Modify: `tests/unit/infra/database/test_config_async.py`
- Create if needed: `tests/unit/infra/database/test_connection_policy.py`
- Modify: `tests/architecture/test_async_db_runtime_boundaries.py`

## Implementation Steps

1. Inventory current env names and update the policy decision table in tests.
2. Add tests first for:
   - direct mode selects `APP_DATABASE_URL` or `DATABASE_URL`.
   - direct mode rejects `-pooler` URLs.
   - pooler mode selects `NullPool` and PgBouncer-safe prepared-statement config.
   - migration URL is not selected for app runtime by default.
3. Extract URL normalization/sanitization into a testable helper if
   `config_async.py` would exceed the 200-line target.
4. Add a guard test that prevents reintroducing implicit
   `DATABASE_URL_DIRECT or DATABASE_URL` app-runtime priority.
5. Keep compatibility fallback for local dev when only legacy `DATABASE_URL` is
   set, but document the fallback as transitional.

## Success Criteria

- [x] Tests prove app runtime no longer silently prefers `DATABASE_URL_DIRECT`.
- [x] Unsafe `direct_pool` + `-pooler` config fails at startup with clear error.
- [x] Pooler mode has explicit asyncpg/PgBouncer compatibility settings.
- [x] Migration URL utility remains direct and unaffected.
- [x] Static guard prevents future ambiguity.

## Risk Assessment

Risk: env rename breaks deployed services.

Mitigation: support old `DATABASE_URL` fallback during rollout, update docs and
deployment env before flipping production.

Risk: prepared-statement fix differs between raw asyncpg and SQLAlchemy asyncpg.

Mitigation: use SQLAlchemy asyncpg documented `prepared_statement_cache_size=0`
and dynamic-name option only in pooler mode tests.
