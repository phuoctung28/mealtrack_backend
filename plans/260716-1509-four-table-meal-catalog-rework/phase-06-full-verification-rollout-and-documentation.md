---
phase: 6
title: "Full Verification Rollout And Documentation"
status: pending
priority: P1
effort: "2d"
dependencies: [5]
mode: tdd
---

# Phase 6: Full Verification Rollout And Documentation

## Overview

Verify migration, import, recommendation, learning, compatibility, and rollout behavior as one production-ready minimal slice.

## Requirements

- Focused unit/migration suites, architecture imports, lint, type check, live PostgreSQL concurrency/import checks, and 180-meal dry-run/import proof.
- Update architecture, database, API, roadmap, and changelog docs to match exactly four tables and deferred learned ranking.
- Default-off feature gate and rollback procedure remain operational.

## File Inventory

| Action | Files |
|---|---|
| Modify docs | `docs/database-guide.md`, `docs/api-endpoints.md`, `docs/system-architecture.md`, `docs/project-roadmap.md`, `docs/project-changelog.md` if present |
| Verify | all touched source, migration, scripts, fixtures, and tests from Phases 1-5 |
| Retire references | old 12-table plan assumptions and release/version/source/rights terminology |

## Tests Before

1. Build a final traceability matrix from each approved requirement to a test.
2. Confirm no accepted decision relies only on mocks when a PostgreSQL invariant is involved.

## Verification Steps

1. Run `alembic heads`; require one head. Upgrade/downgrade/upgrade an empty PostgreSQL database.
2. Run importer dry-run, first import, identical replay, exact duplicate, near-duplicate, unresolved ingredient, rollback, and concurrent importer scenarios.
3. Load the real 180-meal corpus; require zero unresolved ingredients/exact duplicates and reviewed disposition for all near matches.
4. Run concurrent create/swap/log/skip harnesses with owner isolation.
5. Run focused tests, then `pytest tests/unit/`, Ruff, mypy, import-linter, and `git diff --check`.
6. Measure create/read p95 with the real catalog; document the representative environment and threshold.
7. Confirm default-off gate, internal allowlist/cohort behavior, analytics privacy, disable path, and rollback.
8. Update docs and perform whole-plan stale-term sweep.
9. Search source/tests for `catalog_release_id|recipe_version_id|MealRecommendationSwapORM|MealRecommendationInteractionORM`; every remaining occurrence must be an intentional compatibility alias or removed.

## Regression Gate

```bash
.venv/bin/python3.13 -m pytest -q tests/unit/
.venv/bin/python3.13 -m pytest -q tests/migrations/
.venv/bin/ruff check src tests scripts
.venv/bin/mypy src
.venv/bin/lint-imports
git diff --check
```

## Success Criteria

- [ ] Exactly four feature tables verified in migration and live test DB.
- [ ] 180-meal import is additive, deterministic, atomic, and duplicate-safe.
- [ ] All recommendation and AI-suggestion regressions pass.
- [ ] No stale 12-table/release/version/event claim remains in active docs.
- [ ] Rollout and rollback evidence is recorded.

## Risks And Security

Do not enable the feature with unresolved catalog rows, failed concurrency checks, or sensitive analytics properties. If full-suite failures are unrelated, document evidence; never suppress them.

## Next Steps

After review, implement via `/ck:cook <plan>/plan.md --tdd`. Learned ranking remains a separate future plan after a defined data-volume gate.
