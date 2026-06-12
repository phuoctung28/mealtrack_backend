---
title: "Architecture alignment and regression audit"
description: "Docs-only plan for keeping future MealTrack backend features aligned with Clean Architecture, CQRS, async runtime, connection pooling, cache policy, and security boundaries."
status: planned
priority: P1
effort: "1-2 weeks"
branch: "delivery"
tags: [backend, architecture, cqrs, async, docs, security]
created: "2026-06-12T19:10:00+07:00"
createdBy: "ck:docs"
source: skill
mode: docs-only
---

# Architecture Alignment And Regression Audit

## Overview

This is an implementation-ready plan, not an implementation. It records the
current async/CQRS baseline, the bottlenecks and regressions found during the
docs audit, and the order to execute cleanup later.

Primary reference:
[`docs/architecture/async-cqrs-feature-alignment.md`](../../docs/architecture/async-cqrs-feature-alignment.md)

Reports:
- [Architecture alignment scout report](./reports/architecture-alignment-scout-report.md)
- [Repository security threat model](./reports/security-threat-model.md)

## Verified Baseline

- App runtime DB path is async: `config_async.py`, `connection_policy.py`,
  `uow_async.py`, async repositories, and `AsyncUnitOfWork`.
- Sync DB config remains migration/admin-only.
- CQRS event bus is singleton-based and clones stateful handlers for fresh UoW
  instances.
- Route/event-bus unmanaged task creation and direct route commits are guarded by
  architecture tests.
- Import-linter contracts are green, but several green paths rely on explicit
  baseline allowlists.

Validation run on 2026-06-12: 14 architecture tests passed, and import-linter
kept 4 contracts with 0 broken.

## Phases

| Phase | Name | Status |
|---|---|---|
| 1 | [Exception boundary relocation](./phase-01-exception-boundary-relocation.md) | Complete |
| 2 | [App-to-infra baseline shrink](./phase-02-app-to-infra-baseline-shrink.md) | Planned (incremental) |
| 3 | [Background task ownership](./phase-03-background-task-ownership.md) | Complete |
| 4 | [Cache invalidation latency decision](./phase-04-cache-invalidation-latency-decision.md) | Planned (needs prod data) |
| 5 | [RevenueCat and external trust boundaries](./phase-05-revenuecat-external-trust-boundaries.md) | Planned (run per feature) |
| 6 | [Guardrail expansion](./phase-06-guardrail-expansion.md) | Complete |

## Validation Plan

Targeted gates for phase execution:

```bash
.venv/bin/pytest tests/architecture/test_async_boundary_hygiene.py tests/architecture/test_async_db_runtime_boundaries.py -q
.venv/bin/lint-imports
.venv/bin/ruff check <touched files>
```

Before merge, also run `.venv/bin/pytest -q` and `.venv/bin/mypy src`.

## Docs Impact

Major docs impact: future feature pattern is now documented in
`docs/architecture/async-cqrs-feature-alignment.md`.

## Unresolved Questions

None.
