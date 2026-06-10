---
phase: 8
title: "Sync Runtime Deletion and Release Validation"
status: completed
priority: P1
effort: "3-5 days"
dependencies: [7]
---

# Phase 8: Sync Runtime Deletion and Release Validation

## Overview

Delete sync runtime code and run full validation after all consumers have moved to async.

## Requirements

- Functional: remove sync `UnitOfWork`, sync repositories, runtime sync DB config, and sync repository tests.
- Functional: isolate any migration-only sync needs from runtime imports.
- Functional: update docs to reflect async-only runtime.
- Non-functional: no confidential config changes.

## Architecture

Final runtime DB stack:

- neutral ORM `Base`
- async engine/session factory
- `AsyncUnitOfWork`
- async repositories
- migration-only DB config only if Alembic still requires it

## Related Code Files

- Delete: `src/infra/database/uow.py`
- Delete: `src/infra/database/config.py`
- Delete: sync repository files with no consumers
- Modify: `migrations/env.py`
- Modify: `pyproject.toml` and requirements only if psycopg2 no longer needed
- Modify: `docs/standards/db-api.md`
- Modify: `docs/cqrs-guide.md`
- Modify: `docs/system-architecture.md`
- Modify: `docs/project-roadmap.md`
- Modify: `docs/project-changelog.md` if present

## Implementation Steps

1. Run static searches for sync runtime imports and internal repository commits.
2. Delete sync repository and UoW files with no consumers.
3. Decide whether `psycopg2` remains migration-only or can be removed.
4. Update Alembic env/config imports.
5. Remove transition allowlists from architecture tests.
6. Update docs and changelog.
7. Run full validation suite.

## Success Criteria

- [x] Static searches find no runtime sync DB usage.
- [x] Architecture tests have no broad transition allowlist.
- [x] Full `pytest` passes.
- [ ] `ruff check src tests` passes.
- [ ] `mypy src` passes or existing unrelated failures are documented.
- [x] `lint-imports` passes.
- [x] Docs describe async-only runtime.

## Risk Assessment

Risk: deleting sync config can break Alembic or local scripts.

Mitigation: keep migration-only config if needed, but name and document it so runtime cannot import it accidentally.

## Progress Notes

- Removed `src/api/main.py` from the sync DB runtime transition allowlist by moving startup connection warming to `async_engine`.
- Removed `src/api/base_dependencies.py` from the sync DB runtime transition allowlist; the remaining direct sync config/UoW imports are legacy infra files only.
- Deleted the unused sync `src/infra/repositories/meal_translation_repository.py`; meal translation runtime and tests now use `AsyncMealTranslationRepository` or the UoW adapter.
- Deleted sync `src/infra/repositories/food_reference_repository.py` after moving projection/child-row helpers into `food_reference_projection.py` and wiring `AsyncFoodReferenceRepository` to those helpers.
- Deleted the sync notification repository/query-builder path and moved the stale-processing reclaim constant into `CronNotificationDispatchService`; notification persistence now uses `AsyncNotificationRepository`.
- Deleted sync `UnitOfWork`/`UnitOfWorkPort`; handlers now type against `AsyncUnitOfWorkPort`, and the Redis-backed meal-suggestion sentinel lives in `uow_async.py`.
- Deleted unreferenced sync repository helpers for cheat days, saved suggestions, and notification sub-operations; the architecture allowlist now only covers remaining test-coupled sync repository files.
- Deleted remaining sync DB runtime/config and sync repository files: `src/infra/database/config.py`, `src/infra/repositories/base.py`, `meal_repository.py`, `user_repository.py`, `subscription_repository.py`, `weekly_budget_repository.py`, `pending_meal_image_repository.py`, and `pgvector_meal_image_cache_repository.py`.
- Replaced remaining sync repository test consumers with explicit test-only facades in `tests/conftest.py` and removed stale `ScopedSession` patches.
- Tightened `tests/architecture/test_async_db_runtime_boundaries.py`: sync DB import allowlist is empty; repository transaction allowlist is limited to pgvector cache recovery.
- Validation on 2026-06-09: `.venv/bin/pytest -q` passed with `1499 passed, 3 skipped`.
- `lint-imports` passed with all 4 contracts kept after updating the API-to-infra baseline from deleted sync modules to current async wiring.
- `ruff check src tests` remains blocked by existing repo-wide lint debt: `1982` findings, mostly import order and Python 3.10+ annotation modernization.
- `mypy src` remains blocked by existing repo-wide typing/stub debt: `704` errors across `136` files, including missing third-party stubs and older SQLAlchemy/domain typing issues.
