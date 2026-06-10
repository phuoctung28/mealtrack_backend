---
title: "Neon direct pool and async library alignment"
description: "Make database connection mode explicit, prefer direct Neon URL with app-owned async pooling, and remove or contain sync runtime libraries in async paths."
status: complete
priority: P1
effort: "1-2 weeks"
branch: "architecture/sync-to-async"
tags: [backend, database, infra, async, critical]
blockedBy: []
blocks: []
created: "2026-06-10T03:38:16.985Z"
createdBy: "ck:plan"
source: skill
mode: hard
---

# Neon direct pool and async library alignment

## Overview

Follow up the async repository consolidation with two runtime hardening tracks:

1. Make Neon connection behavior explicit. Production app traffic should use a
   direct Neon URL with a small SQLAlchemy async pool. Neon pooler remains a
   deliberate mode for connection-explosion scenarios and must disable asyncpg
   prepared statement caching / use PgBouncer-safe settings.
2. Align active async request/background paths with async-compatible libraries.
   Replace `requests` in async-looking service adapters with `httpx.AsyncClient`
   or move unavoidable sync SDK calls behind explicit off-loop boundaries.

Expected output: code, config, tests, docs, and rollout guidance that remove
implicit pooler/direct ambiguity and prevent sync library calls from blocking the
event loop.

## Scope Challenge

- Existing code: `config_async.py` already supports `AsyncAdaptedQueuePool`, but
  URL priority and env docs conflict. `FoodDataService` uses `requests`; several
  external adapters already use `httpx.AsyncClient`; Cloudinary SDK is sync.
- Minimum changes: explicit DB mode resolver, direct-pool default for app
  runtime, pooler compatibility mode, async USDA client, Cloudinary off-loop
  boundary, docs/tests.
- Complexity: touches infra config, health, docs, tests, and 2 adapter families.
  Five phases are warranted because DB policy and external-client refactor have
  different rollback/verification paths.
- Selected mode: HOLD SCOPE, hard planning. No product/API behavior changes.

## Architecture Direction

Runtime DB modes:

- `direct_pool`: app uses direct Neon URL and SQLAlchemy `AsyncAdaptedQueuePool`.
- `neon_pooler`: app uses Neon `-pooler` URL, SQLAlchemy `NullPool`, and
  PgBouncer-safe asyncpg prepared statement settings.
- migrations/admin scripts always use a direct URL and a migration-only sync
  engine until Alembic strategy changes in a separate plan.

Preferred env contract:

- `APP_DATABASE_URL`: app runtime URL. In production this should be direct Neon.
- `DATABASE_URL_DIRECT` or `MIGRATION_DATABASE_URL`: migration/admin direct URL.
- `DB_CONNECTION_MODE=direct_pool|neon_pooler`.
- `ASYNC_POOL_SIZE_PER_WORKER`, `ASYNC_POOL_MAX_OVERFLOW`,
  `ASYNC_POOL_TIMEOUT`, `ASYNC_POOL_RECYCLE`.

## Research Inputs

- [Runtime connection research](./research/runtime-connection-research.md)
- [Async library scout](./research/async-library-scout.md)
- [Red-team review](./reports/red-team-review.md)
- Official references:
  - Neon connection pooling: <https://neon.com/docs/connect/connection-pooling>
  - Neon connection type guide: <https://neon.com/docs/connect/choose-connection>
  - SQLAlchemy asyncpg dialect: <https://docs.sqlalchemy.org/en/21/dialects/postgresql.html>
  - asyncpg FAQ: <https://magicstack.github.io/asyncpg/current/faq.html>

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Connection policy and guardrails](./phase-01-connection-policy-and-guardrails.md) | Complete |
| 2 | [Direct async DB pool implementation](./phase-02-direct-async-db-pool-implementation.md) | Complete |
| 3 | [Async external client alignment](./phase-03-async-external-client-alignment.md) | Complete |
| 4 | [Configuration docs and rollout](./phase-04-configuration-docs-and-rollout.md) | Complete |
| 5 | [Verification and release readiness](./phase-05-verification-and-release-readiness.md) | Complete |

## Dependencies

- Async repository consolidation is completed and provides the async DB runtime
  baseline: `../260609-1448-async-repository-consolidation/plan.md`.
- Normalized DB refactor is completed and provides current Alembic/model shape:
  `../260609-1134-normalized-database-refactor-migration/plan.md`.
- No unfinished project-local plan blocks this work.
- Keep `psycopg2-binary` migration-only unless a separate Alembic driver plan is
  approved.

## Not In Scope

- DB schema changes.
- API response changes.
- Moving off Neon.
- Replacing Cloudinary as a storage provider.
- Rewriting every HTTP adapter lifecycle into one shared client factory.
- Removing `psycopg2-binary` before migration tooling is redesigned.

## Validation Plan

- Unit tests for DB mode/url resolution, pool class selection, and pooler
  prepared-statement safeguards.
- Unit tests for async USDA client and Cloudinary off-loop boundary.
- Architecture/static guard for active runtime `requests` imports.
- Targeted tests: `tests/unit/infra/database/test_config_async.py`,
  Cloudinary adapter tests, food-data-service tests, health route tests.
- Full gates after implementation: `pytest -q`, `lint-imports`,
  targeted `ruff check` on touched files, and runtime smoke check if env exists.
