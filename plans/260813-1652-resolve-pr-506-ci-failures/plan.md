---
title: "Resolve PR 506 CI Failures"
description: "Align PR #506 with the meal-scan and OpenAI strict-schema contracts, then fix the unrelated recommendation projection failure blocking CI."
status: completed
priority: P1
effort: "2h"
issue: 506
branch: "seer/fix/ai-vision-schema-validation"
tags: [bugfix, backend, ai, reliability]
blockedBy: []
blocks: []
created: 2026-08-13
---

# Resolve PR 506 CI Failures

## Overview

Resolve all seven failures in PR #506 CI run `31660621297`. Six failures come
from incomplete AI contract/test updates. One recommendation failure reproduces
on `main` and requires a small stale-state projection fix.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Preserve beverage-as-food behavior and valid OpenAI strict schemas | P1 |
| 2 | Make reloaded catalog relationships override transient projection data | P1 |
| 3 | Restore the CI-aligned unit suite | P1 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Resolve and Verify CI Failures](./phase-01-start.md) | Completed |

## Dependencies

- Related, non-blocking plan: `plans/260727-1905-slot-only-recommendation-replenishment/`.
- Official OpenAI Structured Outputs contract: all object properties remain in
  `required`; nullable values use a union with `null`.

## Success Criteria

- [x] All seven failed test nodes pass locally.
- [x] `pytest tests/unit --cov=src --cov-fail-under=65` passes.
- [x] Ruff and Python compilation pass for touched files.
- [x] PR #506 head is updated and required checks become green.

## Verification

- Focused: 70 passed.
- Unit suite: 2,273 passed; 79.43% coverage.
- Architecture contracts: 4 kept, 0 broken.
- GitHub Actions run `31689660315`: successful.
- Independent code review: passed with no blockers.

## Docs Impact

None. No user-visible API, database, setup, or architecture contract changes.

<!-- slug: resolve-pr-506-ci-failures -->
