---
phase: 2
title: "Direct async DB pool implementation"
status: complete
priority: P1
effort: "2-3 days"
dependencies: [1]
---

# Phase 2: Direct async DB pool implementation

## Context Links

- Phase 1 policy: `./phase-01-connection-policy-and-guardrails.md`
- Runtime config: `src/infra/database/config_async.py`
- Health routes: `src/api/routes/v1/health.py`
- Settings: `src/infra/config/settings.py`

## Overview

Implement the selected direct Neon URL + app-owned async pool behavior. Preserve
pooler mode only as an explicit alternate mode.

## Requirements

- Functional: `direct_pool` creates an `AsyncAdaptedQueuePool` engine.
- Functional: pool capacity is small and derived from worker count.
- Functional: health endpoint reports connection mode and meaningful capacity.
- Non-functional: avoid double pooling with Neon pooler.
- Non-functional: startup errors are explicit and non-secret.

## Architecture

Direct mode:

```text
FastAPI worker -> SQLAlchemy AsyncAdaptedQueuePool -> direct Neon endpoint
```

Pooler mode:

```text
FastAPI request -> SQLAlchemy NullPool -> Neon PgBouncer transaction pooler
```

Connection budget:

```text
total_app_capacity = (service_instances * workers * pool_size_per_worker)
                     + (service_instances * max_overflow)
```

The implementation should log sanitized host/mode/pool numbers, never full URLs.

## Related Code Files

- Modify: `src/infra/database/config_async.py`
- Modify/Create: `src/infra/database/connection_policy.py`
- Modify: `src/api/routes/v1/health.py`
- Modify: `src/infra/config/settings.py`
- Modify: `tests/unit/infra/database/test_config_async.py`
- Modify: `tests/unit/api/test_health_router.py`

## Implementation Steps

1. Wire the policy object into `create_async_engine`.
2. In `direct_pool`, use:
   - `poolclass=AsyncAdaptedQueuePool`
   - `pool_size=_UVICORN_WORKERS * _ASYNC_POOL_SIZE`
   - `max_overflow=_ASYNC_POOL_OVERFLOW`
   - `pool_timeout`, `pool_recycle`, `pool_pre_ping=True`
3. In `neon_pooler`, use:
   - `poolclass=NullPool`
   - `prepared_statement_cache_size=0` or documented equivalent
   - optional dynamic prepared statement name function if tests show needed
4. Fix env variable naming drift:
   - keep old `POOL_SIZE_PER_WORKER` as temporary fallback only if required.
   - prefer `ASYNC_POOL_SIZE_PER_WORKER`.
5. Update `/v1/health/db-pool` to report:
   - `connection_mode`
   - `pool_type`
   - direct/pooler host classification
   - pool capacity for direct mode
   - pooler note for pooler mode
6. Add tests for both mode outputs and sanitized error messages.

## Success Criteria

- [x] Direct mode uses app-owned async queue pool against direct Neon URL.
- [x] Pooler mode uses `NullPool` and prepared-statement-safe settings.
- [x] Health endpoint reflects the selected mode accurately.
- [x] No secrets appear in logs, errors, or health responses.
- [x] Existing async UoW/session tests still pass.

## Risk Assessment

Risk: direct pool can exhaust Neon `max_connections`.

Mitigation: require small defaults, document formula, and add health visibility.

Risk: local dev lacks `APP_DATABASE_URL`.

Mitigation: fallback to `DATABASE_URL` in non-production/local contexts, but keep
production docs explicit.
