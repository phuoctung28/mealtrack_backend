---
title: "Slot-Only Recommendation Replenishment"
description: "Replace exhausted swap candidates for one recommendation slot without changing the remaining plan."
status: in-progress
priority: P1
effort: "4-6d"
branch: delivery
tags: [feature, backend, database, api, mobile]
blockedBy: []
blocks: []
created: 2026-07-27
source: ck:plan-hard
---

# Slot-Only Recommendation Replenishment

## Decision

Keep the three-day plan length. A swap consumes unseen candidates in its own six-meal slot pool. Once exhausted, replenish only that slot with five fresh alternatives; retain its current selected meal and leave every other slot unchanged. Do not add daily cron/pre-generation or Meal Insight work in this slice.

## Why

Current automatic swap chooses the lowest-ranked inactive row. After one swap, the original rank-0 row is inactive again, so repeated automatic swaps cycle instead of offering new meals. The plan must retain durable seen/pool state; operation history alone cannot reliably distinguish the initial selected candidate from an unshown one.

## Mobile Decision

No Flutter production change is required if `POST /swap` keeps returning the existing `MealRecommendationSlotDetailResponse`. The client already patches one returned slot into its cache. Add mobile contract tests only if backend response fields change; this plan forbids such fields unless implementation proves the current shape insufficient.

## Phases

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Characterize swap semantics and persist candidate-pool lifecycle | In Progress |
| 2 | Replenish only an exhausted slot under concurrency control | In Progress |
| 3 | Verify HTTP/mobile compatibility, observability, docs, and release gates | Pending |

## Non-Goals

- Full-plan regeneration or mutation.
- Re-ranking on every swap.
- Daily cron, one-day readiness, notifications, or a durable worker.
- Meal Insight generation changes.
- Changes to `/v1/meal-suggestions`.

## Cross-Plan Relationship

This extends the completed-local performance redesign’s targeted mutation contract. It must preserve that plan’s invariants: lock one slot, return one slot, and avoid full-plan hydration. No blocking dependency is needed because the contract is already present on `delivery`.

## Success Metrics

- Automatic swaps traverse unseen stored candidates before replenishment.
- Replenishment changes only the requested slot and returns the existing delta response shape.
- A concurrent/stale swap cannot create duplicate candidate pools or overwrite another selection.
- Replenishment and normal swap emit separate bounded latency metrics; no full-plan hydration.
- Existing Flutter slot-cache patch tests remain green without source changes.

## Validation Log

### Implementation Progress

- Branch created: `codex/slot-only-recommendation-replenishment`.
- Added candidate lifecycle migration and slot-scoped replenishment implementation.
- Current validation: 75 focused recommendation/migration tests passed; changed-module mypy and Ruff passed.
- PostgreSQL integration, Flutter focused validation, and staging pool metrics remain release gates.

### Research Findings

- Backend uses a slot-scoped `FOR UPDATE` loader and optimistic `selection_version` for swap.
- Five alternatives are persisted per slot; all inactive rows presently remain eligible, causing rank-0/rank-1 cycling.
- Flutter consumes slot-scoped mutation responses and patches only that slot; backend-compatible behavior needs no mobile implementation change.

### Verification Results

- **Tier:** Standard
- **Claims checked:** 14
- **Verified:** 14 | **Failed:** 0 | **Unverified:** 0
- Verified handler composition at `src/api/dependencies/event_bus.py:596-604`, slot lock at `src/infra/repositories/meal_recommendation_plan_repository_async.py:508-523`, and the five-alternative selector at `src/domain/services/meal_recommendation/three_day_plan_optimizer.py:208-257`.

## Red Team Review

### Accepted Findings

- Corrected swap-count acceptance: the initially selected meal is already seen, therefore five stored alternatives are consumed before the sixth automatic swap replenishes the pool.
- Concurrent refresh needs a persistence-level duplicate-candidate guard in addition to slot locking and optimistic version recheck.
- Legacy candidate history cannot be reconstructed. Migration must only mark the current selected row as seen and document that strict no-repeat behavior starts with the new lifecycle state.

### Whole-Plan Consistency Sweep

- Files reread: `plan.md`, all three phase files.
- Decision deltas checked: swap count, concurrent candidate uniqueness, legacy history behavior.
- Reconciled stale references: 2.
- Unresolved contradictions: 0.

## Unresolved Questions

- None. Product decisions are locked above.
