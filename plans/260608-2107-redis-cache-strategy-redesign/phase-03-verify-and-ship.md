---
phase: 3
title: Verify and ship
status: completed
priority: P1
effort: 1h
dependencies:
  - 2
---

# Phase 3: Verify and ship

## Overview

Run focused verification, review the diff for side effects, commit, push, and create a PR.

## Requirements

- Functional: targeted tests covering modified Redis/session/cache code pass.
- Non-functional: no syntax/lint regressions in touched modules; no secrets staged.

## Architecture

Verification must cover the actual cache boundaries changed in Phase 2 and confirm notification Redis removal remains intact by search.

## Related Code Files

- Verify: `src/infra/cache/redis_client.py`
- Verify: `src/infra/repositories/meal_suggestion_repository.py`
- Verify: `src/domain/services/meal_suggestion/nutrition_lookup_service.py`
- Verify: cache docs changed in this branch

## Implementation Steps

1. Run targeted unit tests for Redis client, meal suggestion repository, nutrition Redis cache, and cache key TTLs.
2. Run `ruff check` on touched Python modules.
3. Run `python -m compileall` for touched Python modules if broader lint is noisy.
4. Review `git diff` for accidental unrelated changes.
5. Stage, scan staged diff for secrets, commit, push, and create PR.

## Success Criteria

- [ ] Focused tests pass or any failure is clearly unrelated and reported.
- [ ] Touched Python files pass lint/syntax verification.
- [ ] Git commit contains only intended docs/code/test changes.
- [ ] PR is opened against the repository default target branch.

## Risk Assessment

Full suite may be too slow for this PR. If not run, explicitly report that only focused verification was completed.
