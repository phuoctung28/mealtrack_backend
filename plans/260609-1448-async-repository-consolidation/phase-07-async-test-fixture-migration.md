---
phase: 7
title: "Async Test Fixture Migration"
status: completed
priority: P1
effort: "4-6 days"
dependencies: [6]
---

# Phase 7: Async Test Fixture Migration

## Overview

Remove test wrappers and fixtures that make sync repositories look async, so tests exercise the real runtime contract.

## Requirements

- Functional: tests use async repository fixtures or async fakes.
- Functional: `AsyncSyncRepoWrapper` and local sync-to-async wrappers are removed.
- Functional: repository tests cover async behavior directly.
- Non-functional: tests remain deterministic under Python 3.11 async behavior.

## Architecture

Use asyncpg-backed integration fixtures where DB behavior matters. Use async fakes for handler/unit tests. Do not wrap sync repositories in awaitable adapters.

## Related Code Files

- Modify: `tests/conftest.py`
- Modify: `tests/integration/infra/repositories/conftest.py`
- Modify: `tests/fixtures/fakes/*.py`
- Modify: `tests/unit/repositories/*.py`
- Modify: `tests/unit/infra/repositories/*.py`
- Modify: `tests/unit/handlers/**/*.py`
- Modify: `tests/integration/**/*.py`

## Implementation Steps

1. Replace `AsyncSyncRepoWrapper` with real async fake/repository fixtures.
2. Convert core repository tests to async versions.
3. Convert delete-user and handler wrappers to async fake UoW/repo objects.
4. Keep factory commits only inside test setup utilities, not runtime repository tests.
5. Update architecture tests to tighten allowlists.
6. Run targeted test directories, then full pytest.

## Success Criteria

- [x] No tests use sync-to-async repository wrappers.
- [x] Repository tests use async repository implementations.
- [x] Handler tests use async fake UoW/repositories.
- [x] Full test suite passes or remaining failures are documented as unrelated.

## Risk Assessment

Risk: async fixtures can be slower and more complex.

Mitigation: use async fakes for unit tests and reserve async DB fixtures for integration tests.

## Progress Notes

- Removed the generic `AsyncSyncRepoWrapper` from `tests/conftest.py`.
- Replaced magic wrapping in `TestUnitOfWork` with explicit async test facades for meal and user repository methods used by legacy sync-session handler tests.
- Added an architecture guard that fails if the generic wrapper pattern is reintroduced under `tests/`.
- Verified the event-bus handler tests that use `TestUnitOfWork`.
- Replaced delete-user local wrapper classes with explicit SQLite-backed async test doubles.
- Removed async compatibility shims from legacy sync repositories (`BaseRepository`, `SubscriptionRepository`) and their shim tests.
- Added an architecture guard against legacy sync repository async-compatibility method names.
- Migrated food-reference SQL behavior tests from sync `SessionLocal` patching to `AsyncFoodReferenceRepository`.
- Kept real-Postgres integration no-op `mock_scoped_session` overrides because they intentionally prevent the root autouse sync fixture patch from interfering with their own session lifecycle.
- Removed the unit notification repository test's dependency on the root `ScopedSession` fixture by patching the legacy repository's own session factory directly.
- Migrated promo-code and unified-code handler tests off repository constructor patching; their fake UoWs now expose `promo_codes` and `referrals` like runtime.
- Removed root and integration API `ScopedSession` fixture patches after deleting the sync DB runtime.
- Replaced remaining sync repository test consumers with explicit async test facades or canonical async repositories.
- Full pytest validation passed after the fixture migration.

## Remaining Work

- None for this plan. Historical sync-repository coverage was either deleted with the runtime or replaced by async/test-only facades.
