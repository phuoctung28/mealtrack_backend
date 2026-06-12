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

Run focused verification, update plan state, commit, push, and open a PR.

## Requirements

- Functional: all acceptance criteria from `plan.md` verified by tests or explicit inspection.
- Non-functional: no lint/syntax errors in touched files, no secrets staged, branch pushed for PR review.

## Architecture

Verification should cover the real API boundary where possible and the isolated provider/service units where DB or external APIs are mocked.

## Related Code Files

- Verify: touched `src/` files.
- Verify: touched `tests/` files.
- Verify: `plans/260608-2251-ai-api-reliability-hardening/*`.

## Implementation Steps

1. Run focused AI/provider/vision/handler tests with Python 3.11.
2. Run route tests for meal suggestions and ingredients using the repo environment.
3. Run ruff on touched Python files.
4. Run `git diff --check` and inspect final diff.
5. Mark plan phases complete with `ck plan check`.
6. Stage, secret-scan, commit, push, and open PR against `main`.

## Success Criteria

- [ ] Focused tests pass.
- [ ] Route tests pass or any remaining blocker is documented with concrete cause.
- [ ] Ruff passes on touched files.
- [ ] Git secret scan passes.
- [ ] PR URL returned.

## Risk Assessment

If route tests require live services beyond local Postgres, stop and report the exact boundary rather than claiming full route confidence.
