---
phase: 5
title: "Verification and release readiness"
status: complete
priority: P1
effort: "1-2 days"
dependencies: [2, 3, 4]
---

# Phase 5: Verification and release readiness

## Context Links

- All prior phases
- Architecture guard tests: `tests/architecture/`
- Import linter: `.importlinter`
- Runtime health routes: `src/api/routes/v1/health.py`

## Overview

Prove the DB runtime, external adapters, docs, and rollout checks are coherent
before this ships.

## Requirements

- Functional: test suite proves both direct-pool and pooler modes.
- Functional: converted async clients preserve existing behavior.
- Functional: docs and config agree with code.
- Non-functional: no new import-boundary violation.
- Non-functional: no unmanaged sync library call remains in async runtime paths.

## Architecture

Verification has three layers:

1. Static: grep/architecture tests block unsafe sync imports and env drift.
2. Unit/focused: DB policy, adapter behavior, health responses.
3. Runtime smoke: optional real Neon staging connection if env available.

## Related Code Files

- Modify: `tests/architecture/test_async_db_runtime_boundaries.py`
- Modify/Create: DB config tests under `tests/unit/infra/database/`
- Modify/Create: adapter tests under `tests/unit/infra/`
- Modify: docs and plan status after verification

## Implementation Steps

1. Run static searches:
   - `rg "DATABASE_URL_DIRECT.*or.*DATABASE_URL" src/infra/database`
   - `rg "import requests|requests\\." src --glob '*.py'`
   - `rg "prepared_statement_cache_size|DB_CONNECTION_MODE|APP_DATABASE_URL" src tests docs .env.example`
2. Run focused unit tests:
   - `.venv/bin/pytest tests/unit/infra/database/test_config_async.py -q`
   - DB policy tests if split into a new file
   - Cloudinary adapter tests
   - FoodDataService tests
   - health route tests
3. Run architecture/import checks:
   - `.venv/bin/pytest tests/architecture/test_async_db_runtime_boundaries.py -q`
   - `lint-imports`
4. Run full suite:
   - `.venv/bin/pytest -q`
5. Run targeted lint on touched files:
   - `.venv/bin/ruff check <touched files>`
   - `black --check <touched python files>`
6. If staging env is available, run a real smoke:
   - deploy with `DB_CONNECTION_MODE=direct_pool`
   - call `/v1/health/db-pool`
   - call one read endpoint and one write endpoint
   - monitor connection count and asyncpg prepared-statement errors.
7. Update plan/docs with final validation results.

## Success Criteria

- [x] Focused DB config/policy tests pass.
- [x] Focused adapter tests pass.
- [x] Architecture/import-linter checks pass.
- [x] Full pytest passes or unrelated pre-existing failures are documented.
- [x] No active runtime `requests` usage remains without explicit off-loop
  classification.
- [x] Staging smoke confirms direct-pool mode if environment is available.

## Risk Assessment

Risk: repo-wide `ruff`/`mypy` have pre-existing debt.

Mitigation: run focused checks on touched files and report repo-wide debt
separately, matching the async consolidation precedent.

Risk: staging smoke unavailable locally.

Mitigation: make the smoke optional but document exact Render/health commands so
deployment verification is repeatable.
