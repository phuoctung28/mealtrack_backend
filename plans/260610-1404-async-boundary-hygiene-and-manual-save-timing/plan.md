---
title: "Async boundary hygiene and manual save timing"
description: "Clean remaining async-boundary debt after async DB migration and prove where manual meal save waits."
status: complete
priority: P1
effort: "1-2 weeks"
branch: "delivery"
tags: [backend, refactor, async, tech-debt, critical]
blockedBy: []
blocks: []
created: "2026-06-10T07:04:31.252Z"
createdBy: "ck:plan"
source: skill
mode: hard
---

# Async Boundary Hygiene and Manual Save Timing

## Overview

Clean remaining async-boundary debt after the async DB runtime migration. This is not a second async repository rewrite. App DB paths are already async; remaining risks are route-level session bypasses, manual commits, unmanaged `asyncio.create_task`, event-loop-driving sync wrappers, compatibility `to_thread` seams, and missing timing proof for `/v1/meals/manual`.

Expected output: tests-first implementation plan, focused guardrails, owned background task behavior, cleaned transaction boundaries, sync-wrapper removal where active callers allow it, and manual meal save timing evidence.

## Scope Challenge

- Existing code: async DB runtime, `AsyncUnitOfWork`, async repositories, async boundary architecture test, cache invalidation service, event bus, and manual meal handler already exist.
- Minimum changes: add guardrails, own background tasks, remove route write/session bypasses, remove unused sync meal-generation wrapper, and instrument/measure manual-save timing before any speculative fix.
- Complexity: touches more than 8 files, but each slice has a different failure mode. Five phases warranted; no broad "make every def async" pass.
- Selected mode: HOLD SCOPE, hard planning. No product behavior or public API contract change unless timing evidence demands a later fix.

## Architecture Direction

- Async DB runtime remains `config_async.py` + `AsyncUnitOfWork` + async repositories.
- Transaction ownership moves toward UoW/handlers, away from route-level commits and direct `uow.session.commit()`.
- Background async work must be awaited by contract, owned by a managed task runner, or moved to a durable queue-like path. No anonymous request-local task spawning for critical work.
- Sync vendor SDK calls may stay behind explicit `to_thread` boundaries when no async SDK exists. Sync compatibility wrappers that drive the event loop are removed or quarantined.
- Manual meal save timing is measured at route, event bus, handler, DB commit, and cache invalidation boundaries before changing behavior.

## Research Inputs

- [Runtime boundary inventory](./research/runtime-boundary-inventory.md)
- [Asyncio usage research](./research/asyncio-usage-research.md)
- [Red team review](./reports/from-planner-to-user-red-team-async-boundary-plan-review-report.md)
- Completed baseline plans:
  - `../260609-1448-async-repository-consolidation/plan.md`
  - `../260610-1038-neon-direct-pool-and-async-library-alignment/plan.md`

## Cross-Plan Dependencies

No unfinished local plan blocks this work. Completed async repository and Neon async-library plans are prerequisite context, not active blockers.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Inventory and guardrails](./phase-01-inventory-and-guardrails.md) | Complete |
| 2 | [Owned background task execution](./phase-02-owned-background-task-execution.md) | Complete |
| 3 | [Transaction boundary cleanup](./phase-03-transaction-boundary-cleanup.md) | Complete |
| 4 | [Sync compatibility wrapper cleanup](./phase-04-sync-compatibility-wrapper-cleanup.md) | Complete |
| 5 | [Manual save timing validation](./phase-05-manual-save-timing-validation.md) | Complete |

## Dependencies

- Python 3.11+ / FastAPI / SQLAlchemy async runtime stays unchanged.
- PostgreSQL/Neon remains the app DB.
- Redis cache invalidation semantics stay conservative until manual-save timing evidence proves a safe change.
- Mobile/API response shapes stay backward compatible.
- Existing architecture guard `tests/architecture/test_async_db_runtime_boundaries.py` remains a required gate.

## Not In Scope

- Reopening the completed async repository migration.
- Rewriting every helper `def` into `async def`.
- Replacing vendor SDKs solely because they are sync.
- Moving event bus to Celery/RQ/Temporal in this round.
- Public API response changes.
- DB schema changes unless a guardrail needs a test-only fixture.

## Validation Plan

- Add tests before refactors in each phase.
- Run targeted tests for architecture guardrails, event bus behavior, feature flags, meal suggestions, meal generation service, and manual meal save timing.
- Run `lint-imports`.
- Run targeted `ruff check` on touched files.
- Treat repo-wide `ruff`/`mypy` debt as non-blocking unless touched files regress.

## Red Team Review

Accepted findings are reflected in the phase files:

- Managed background runner required before event bus publish cleanup.
- Manual-save timing remains evidence-first.
- Route write/session bypass cleanup starts with writes, not every read dependency.
- Sync wrapper removal includes test migration.
- UoW lock behavior change is guarded and deferred unless reuse is proven absent.

### Whole-Plan Consistency Sweep

Checked `plan.md` and all phase files after red-team synthesis. No unresolved contradictions.

## Unresolved Questions

None.
