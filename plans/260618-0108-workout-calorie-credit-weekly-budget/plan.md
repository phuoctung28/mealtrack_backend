---
title: Workout Calorie Credit in Weekly Budget
description: >-
  Make weekly budget redistribution use net calories: food calories minus
  included workout calories.
status: in-progress
priority: P1
branch: feat/workout-calorie-credit-weekly-budget
tags:
  - feature
  - backend
  - nutrition
blockedBy: []
blocks: []
created: '2026-06-17T18:10:50.044Z'
createdBy: 'ck:plan'
source: skill
---

# Workout Calorie Credit in Weekly Budget

## Overview

Weekly budget adjusted nutrition currently recalculates consumed calories from meals only. Daily macros and bulk nutrition already use net calories (`food - included movement`). This plan aligns weekly budget redistribution, remaining calories, and tomorrow preview with the same calorie-balance rule.

Product rule: full logged workout calories count when `include_in_balance = true`. Baseline TDEE excludes planned workouts, so there is no expected-movement offset to subtract. Macro grams remain food-only.

Science basis: when exercise is not already included in the baseline target, logged exercise is additional energy expenditure, so calorie balance should reduce net intake by that expenditure. If exercise were already in TDEE, adding it again would double count; that model is explicitly out of scope.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Regression Tests](./phase-01-regression-tests.md) | Completed |
| 2 | [Implementation](./phase-02-implementation.md) | Completed |
| 3 | [Verification and PR](./phase-03-verification-and-pr.md) | In Progress |

## Dependencies

- Brainstorm source: `plans/reports/260618-0108-workout-calorie-credit-weekly-budget-brainstorm.md`
- Existing movement contract: `docs/superpowers/specs/2026-05-31-movement-api-design.md`
- Existing readiness doc: `docs/movement-release-readiness.md`
