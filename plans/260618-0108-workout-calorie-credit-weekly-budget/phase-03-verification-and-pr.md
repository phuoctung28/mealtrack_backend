---
phase: 3
title: Verification and PR
status: in-progress
priority: P1
effort: 45m
dependencies:
  - 2
---

# Phase 3: Verification and PR

## Overview

Verify the nutrition budget behavior, update project docs, commit, push, and open a PR.

## Requirements

- Functional: targeted tests pass.
- Non-functional: touched files compile and lint cleanly enough for the project gate.
- Non-functional: docs mention the weekly-budget movement credit behavior and TDEE baseline boundary.

## Architecture

Validation stays focused on affected domain/app/repository tests plus Python compile. The PR should describe the product rule and science caveat: full logged workout credit is correct because baseline TDEE does not already include that workout.

## Related Code Files

- Modify: `docs/movement-release-readiness.md`
- Modify: `docs/project-roadmap.md`
- Modify: `docs/project-overview-pdr.md`
- Modify: `docs/architecture/fitness-goals.md`
- Run: targeted pytest, ruff, compileall
- Git: conventional commit, push branch, create PR with `gh`

## Implementation Steps

1. Run targeted tests:
   `uv run pytest tests/unit/domain/services/test_weekly_budget_async.py tests/unit/handlers/query_handlers/test_cached_query_handlers.py tests/unit/handlers/query_handlers/test_movement_balance_integration.py tests/unit/infra/repositories/test_movement_repository_async.py -q`
2. Run lint on touched source/tests.
3. Run Python compile check for `src` and affected tests.
4. Update docs for movement weekly-budget behavior and baseline TDEE boundary.
5. Stage, secret-scan diff, commit with conventional message, push.
6. Create PR against the repository default branch.

## Success Criteria

- [x] Tests pass or any unrelated failures are clearly isolated.
- [x] `ruff check` passes for touched files.
- [x] `python -m compileall` passes for touched source/tests.
- [ ] PR URL is available.
