---
phase: 4
title: "Configuration docs and rollout"
status: complete
priority: P1
effort: "1-2 days"
dependencies: [2, 3]
---

# Phase 4: Configuration docs and rollout

## Context Links

- Env template: `.env.example`
- Database docs: `docs/database-guide.md`
- External services docs: `docs/external-services.md`
- Troubleshooting: `docs/troubleshooting.md`
- Current plan: `./plan.md`

## Overview

Make deployment configuration and docs match the runtime behavior. This phase is
the release-safety layer for Render/Neon env updates.

## Requirements

- Functional: env examples show direct app URL and migration direct URL clearly.
- Functional: docs explain when Neon pooler is acceptable.
- Functional: rollout steps avoid breaking current deploys.
- Non-functional: no secrets in docs or logs.
- Non-functional: docs distinguish app runtime from Alembic migration runtime.

## Architecture

Env contract to document:

```text
DB_CONNECTION_MODE=direct_pool
APP_DATABASE_URL=postgresql://...ep-xxx.region.aws.neon.tech/db?sslmode=require
DATABASE_URL_DIRECT=postgresql://...ep-xxx.region.aws.neon.tech/db?sslmode=require
ASYNC_DB_USE_QUEUE_POOL=true
ASYNC_POOL_SIZE_PER_WORKER=3
ASYNC_POOL_MAX_OVERFLOW=2
```

Pooler fallback:

```text
DB_CONNECTION_MODE=neon_pooler
APP_DATABASE_URL=postgresql://...ep-xxx-pooler.region.aws.neon.tech/db?sslmode=require
```

Pooler mode must mention PgBouncer transaction mode and prepared-statement
constraints.

## Related Code Files

- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/database-guide.md`
- Modify: `docs/external-services.md`
- Modify: `docs/troubleshooting.md`
- Modify: `docs/project-roadmap.md`
- Create optional ADR: `docs/decisions/260610-neon-direct-pool-runtime.md`

## Implementation Steps

1. Update `.env.example` with app/migration URL split and async pool env names.
2. Add a short DB connection policy section to `docs/database-guide.md`.
3. Update `docs/external-services.md` to explain Neon direct vs pooler usage.
4. Add troubleshooting entries for:
   - asyncpg prepared statement errors
   - direct connection exhaustion
   - pooler wait timeout
   - env mismatch startup failure
5. Add ADR only if the implementation introduces a durable policy decision that
   future work should not re-litigate.
6. Add rollout checklist:
   - set env vars in staging
   - verify `/v1/health/db-pool`
   - run migration with direct URL
   - deploy web
   - monitor pg connections and asyncpg prepared-statement errors
   - then production env rollout.

## Success Criteria

- [x] `.env.example` no longer tells app runtime to use Neon pooler by default.
- [x] Docs clearly state when to use pooler vs direct.
- [x] Rollout checklist covers staging and production.
- [x] Troubleshooting maps exact asyncpg/PgBouncer errors to actions.
- [x] Roadmap/changelog note documents the runtime policy change.

## Risk Assessment

Risk: docs drift from actual env names.

Mitigation: write tests for the env names the code actually reads, and mention
those same names in docs.

Risk: operators accidentally set both old and new vars.

Mitigation: startup policy should log selected mode/source and fail on unsafe
production combinations.
