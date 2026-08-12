# Meal Catalog Phase 0 Evidence

This file records Gate A-D evidence for the Phase 0 production foundation. Do not include database URLs, credentials, JWTs, user IDs, search text, meal payloads, or health-goal data.

## Gate Summary

```text
schema_gate=passed
catalog_import_gate=blocked_missing_approved_corpus
auth_and_rate_limit_gate=passed
local_search_gate=passed
postgres_integration_gate=passed
degraded_mode_gate=passed
load_gate=blocked_missing_staging_host_and_token
rollback_drill=blocked_missing_staging_drill
```

Phase 0 implementation is code-ready locally, but Phase 0 is not fully closed
until the approved 180-meal corpus, staging load run, and rollback drill are
recorded.

## Gate A - Schema Safety

Decision: `20260716000001` has not been deployed to production, so this phase can treat the catalog schema as an unshipped migration baseline. Shared-environment read-only Alembic checks are not required before editing this migration family unless another shared environment is later confirmed to have applied it.

| Check | Environment | UTC Time | Operator | Result | Evidence |
|---|---|---:|---|---|---|
| Alembic revision graph has one head | local checkout | 2026-07-23T10:00:32Z | Codex | pass | `ScriptDirectory.get_heads()` returned `["20260716000001"]`. |
| `meal_catalog` has no stored recipe calorie column | local checkout | 2026-07-23T10:00:32Z | Codex | pass | Characterization added in `tests/migrations/test_catalog_recipe_tables_migration.py`. |
| Production deploy status | production | 2026-07-23T10:00:32Z | Alex | not deployed | User confirmed this migration has not deployed to production. |
| Disposable PostgreSQL upgrade/downgrade/upgrade | ephemeral PostgreSQL | pending | pending | optional | Useful before release, but not required to choose an unshipped-migration editing strategy. |

## Gate B - Catalog Readiness

Code-ready; production corpus validation remains blocked on the approved content
files. The local repository does not currently contain
`scripts/data/meal-recommendation-recipes.json` or
`scripts/data/meal-recommendation-resolver-map.json`.

| Check | Environment | UTC Time | Operator | Result | Evidence |
|---|---|---:|---|---|---|
| Canonical additive import hardening | local checkout | 2026-07-23T10:00:32Z | Codex | pass | Importer now prepares the whole manifest before writes, uses a stable content hash, serializes imports, skips exact replays, and withholds near duplicates for review. |
| Deterministic import report | local checkout | 2026-07-23T10:00:32Z | Codex | pass | `--resolver-report` writes manifest digest, recipe count, coverage, import counts, unresolved ingredients, validation errors, and near-duplicate review items. |
| Production corpus files | local checkout | 2026-07-23T10:00:32Z | Codex | blocked | `scripts/data/` only contains `meal_images_seed.csv`; approved 180-meal manifest and resolver map are not present. |
| Production dry-run validation | local checkout or staging | pending | pending | blocked | Run once approved corpus files are available. Expected: `recipe_count=180`, zero validation errors, zero unresolved ingredient issues, zero unreviewed near duplicates. |
| Production import and additive replay | staging | pending | pending | blocked | First run expected `inserted=180`, `skipped_existing=0`; replay expected `inserted=0`, `skipped_existing=180`, same manifest digest. |

## Gate C - Runtime Safety

Pending. Requires protected provider routes, local-first search, and degraded-mode rehearsal.

### Initial Alert Thresholds

| Signal | Threshold | Action |
|---|---:|---|
| Catalog cold snapshot failure | `meal_catalog.snapshot.refresh{status="cold_failure"} > 0` for 5 minutes | Page operator and keep recommendations disabled until a fresh catalog snapshot loads. |
| Food provider error/degraded rate | `food_search.requests{status="degraded"}` > 20% of food search traffic for 10 minutes | Check provider quota/status and confirm local-first search still returns useful results. |
| Recommendation 5xx rate | `meal_recommendation.requests{status="error"}` > 1% for 5 minutes | Page operator and disable recommendation entry points if persistent. |

Dashboard-only signals, not pages: search zero-result rate, seed import review-required rate, seed import rejected count, active catalog meal count, snapshot age, and provider/local/mixed search source mix.

## Gate D - Production Confidence

Partially verified locally. Staging load, dashboard, and rollback evidence remain
pending until staging host/token and approved corpus are available.

| Check | Environment | UTC Time | Operator | Result | Evidence |
|---|---|---:|---|---|---|
| PostgreSQL import flow | ephemeral PostgreSQL | 2026-07-23T10:00:32Z | Codex | pass | `tests/integration/postgres` covers dry-run, replay, rollback-on-invalid-manifest, concurrent import serialization, near-duplicate withholding, and catalog projection. |
| Degraded local food search | ephemeral PostgreSQL | 2026-07-23T10:00:32Z | Codex | pass | `tests/integration/postgres/test_meal_catalog_degraded_mode.py` proves local `food_reference` search returns when Redis cache and provider calls fail. |
| Load profile | local checkout | 2026-07-23T10:00:32Z | Codex | ready | `tests/performance/locust_meal_catalog.py` requires `MEALTRACK_LOAD_TEST_TOKEN` and exercises search, recommendation create/replay, slot detail, swap, and log with named requests. |
| Baseline staging load | staging | pending | pending | blocked | Requires `STAGING_HOST` and `MEALTRACK_LOAD_TEST_TOKEN`; target p95 search/detail/replay <=300 ms, create <=1.5 s, eligible success >=99.95%. |
| Redis/provider degraded load | staging | pending | pending | blocked | Requires staging failure injection. Expected: local search, replay, detail, swap, and log remain available; provider enrichment may degrade to bounded local-only search. |

## Release Gate Command Results

| Command | Environment | Result | Notes |
|---|---|---|---|
| `alembic heads` | local checkout | pass | One head: `20260723000001`. |
| `.venv/bin/python3.13 -m pytest -q tests/unit/` | local checkout | pass | `2011 passed, 14 warnings`. |
| `.venv/bin/python3.13 -m pytest -q tests/migrations/` | local checkout | pass | `20 passed`. |
| `.venv/bin/python3.13 -m pytest tests/integration/postgres -o addopts="" -m integration -q` | ephemeral PostgreSQL | pass | `7 passed`; DB had `vector` and `pg_trgm`. |
| `.venv/bin/lint-imports` | local checkout | pass | 4 architecture contracts kept. |
| focused changed-file Ruff | local checkout | pass | Scoped to files changed for this phase. |
| `.venv/bin/ruff check src tests scripts` | local checkout | blocked | Existing repo-wide Ruff debt: 1,643 findings across unrelated legacy scripts/tests. |
| `.venv/bin/mypy src` | local checkout | blocked | Existing repo-wide type debt: 767 errors across 139 files, including Firebase stubs and older handler contracts. |
| `git diff --check` | local checkout | pass | No whitespace errors. |
