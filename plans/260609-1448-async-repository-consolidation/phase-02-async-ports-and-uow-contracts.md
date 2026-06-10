---
phase: 2
title: "Async Ports and Unit of Work Contracts"
status: completed
priority: P1
effort: "3-4 days"
dependencies: [1]
---

# Phase 2: Async Ports and Unit of Work Contracts

## Overview

Make async contracts explicit so application code stops depending on sync-shaped ports implemented by async methods.

## Requirements

- Functional: repository ports used by app code expose async method signatures.
- Functional: `AsyncUnitOfWorkPort` declares repository attributes, not only context methods.
- Functional: fake repositories remain async-compatible.
- Non-functional: avoid generic sync/async base abstractions.

## Architecture

Use async as the canonical domain persistence contract. Either convert existing port files in place or introduce async-specific ports and migrate references. Prefer in-place conversion if it avoids duplicate abstractions.

## Related Code Files

- Modify: `src/domain/ports/meal_repository_port.py`
- Modify: `src/domain/ports/user_repository_port.py`
- Modify: `src/domain/ports/subscription_repository_port.py`
- Modify: `src/domain/ports/saved_suggestion_repository_port.py`
- Modify: `src/domain/ports/notification_repository_port.py`
- Modify: `src/domain/ports/unit_of_work_port.py`
- Modify: `src/domain/ports/async_unit_of_work_port.py`
- Modify: `src/infra/database/uow_async.py`
- Modify: `tests/fixtures/fakes/*.py`

## Implementation Steps

1. [x] Convert repository port methods that are awaited in handlers to async signatures.
2. [x] Add typed repository attributes to `AsyncUnitOfWorkPort`.
3. [x] Keep sync `UnitOfWorkPort` as a transition artifact while later phases migrate consumers.
4. [x] Update fakes to match async contracts.
5. [x] Add contract tests that fail when repository ports drift back to sync methods.
6. [x] Run targeted handler and fake UoW tests.

## Success Criteria

- [x] No async repository subclass is blocked by a sync-only abstract contract.
- [x] `AsyncUnitOfWorkPort` describes actual repository attributes.
- [x] Fakes match runtime async contracts.
- [x] Existing handler tests pass after async contract changes.

## Completion Notes

- Converted meal, user, subscription, saved suggestion, and notification repository ports to async method signatures.
- Added `AsyncUnitOfWorkPort` repository attributes for the async runtime UoW surface.
- Kept `UnitOfWorkPort` and handler constructor migration for later phases because request-path and cron consumers still use the sync transition surface.
- Added `tests/unit/domain/ports/test_async_repository_contracts.py`.

## Risk Assessment

Risk: broad type changes produce many failing tests.

Mitigation: update fakes and tests in the same phase; do not delete sync implementation files yet.
