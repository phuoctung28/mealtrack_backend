# Phase 8 Report: Final Sync Runtime Removal

## Summary

Removed the remaining sync DB runtime and sync repository files. Runtime source now uses async DB config, `AsyncUnitOfWork`, and async repositories.

## Files Removed

- `src/infra/database/config.py`
- `src/infra/repositories/base.py`
- `src/infra/repositories/meal_repository.py`
- `src/infra/repositories/user_repository.py`
- `src/infra/repositories/subscription_repository.py`
- `src/infra/repositories/weekly_budget_repository.py`
- `src/infra/repositories/pending_meal_image_repository.py`
- `src/infra/repositories/pgvector_meal_image_cache_repository.py`

## Test Harness Changes

- Replaced remaining sync repository test consumers with explicit test-only facades in `tests/conftest.py`.
- Removed stale `ScopedSession` patches from test fixtures.
- Deleted sync-only repository tests whose async replacements already cover the active runtime paths.

## Verification

- `.venv/bin/pytest -q`
  - Result: `1499 passed, 3 skipped`
- `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py tests/unit/infra/database/test_config_async.py tests/unit/infra/database/test_uow_async.py -q`
  - Result: `18 passed`
- `.venv/bin/ruff check --select F401,E9 src/api/dependencies/auth.py tests/conftest.py tests/integration/api/conftest.py tests/architecture/test_async_db_runtime_boundaries.py`
  - Result: passed
- Static search for deleted sync runtime imports:
  - Result: no runtime source hits; only architecture guard string literals remain.
- `lint-imports`
  - Result: 4 contracts kept, 0 broken

## Known Non-Blocking Gates

- `ruff check src tests` reports existing repo-wide lint debt: `1982` findings.
- `mypy src` reports existing repo-wide typing/stub debt: `704` errors across `136` files.

## Unresolved Questions

None.
