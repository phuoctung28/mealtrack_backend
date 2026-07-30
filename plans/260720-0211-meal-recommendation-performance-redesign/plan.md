---
title: "Meal Recommendation Performance Redesign"
description: "Remove repeated catalog/history hydration, synchronous analytics, full-plan mutations, and blank mobile loading from catalog recommendations."
status: completed-local
priority: P1
effort: "10-14d"
branch: "delivery"
tags: [performance, backend, mobile, database, api, tdd, critical]
blockedBy: []
blocks: []
created: "2026-07-19T19:13:01.327Z"
createdBy: "ck:plan"
source: skill
mode: deep-tdd
---

# Meal Recommendation Performance Redesign

## Overview

Keep the deterministic four-table recommendation model, but make catalog work process-local and reusable, replace full meal-history hydration with one aggregate query, return compact or target-slot projections, move analytics off the request path, and let Flutter render cached data immediately while it refreshes.

## Scope Decision

- Keep: four feature tables, `food_reference` authority, backend-derived calories, deterministic output, owner scoping, operation replay, and separate `/v1/meal-suggestions` behavior.
- Add: immutable process-local catalog snapshot, revision/TTL refresh, one-pass ranked pools, compact plan responses, slot mutation responses, lazy slot detail, stage metrics, and mobile stale-while-revalidate.
- Replace: the current unreleased full-plan HTTP contract and matching Flutter models directly.
- Defer: Redis recommendation-result cache, vectors/ML ranking, background plan generation, catalog schema redesign, and speculative indexes.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Baseline And Contract Characterization](./phase-01-baseline-and-contract-characterization.md) | Completed |
| 2 | [Nonblocking Observability And Summary Contract](./phase-02-nonblocking-observability-and-summary-contract.md) | Completed |
| 3 | [Process-Local Catalog Snapshot And Ranking](./phase-03-process-local-catalog-snapshot-and-ranking.md) | Completed |
| 4 | [Aggregate Affinity And Fast Generation](./phase-04-aggregate-affinity-and-fast-generation.md) | Completed except staging p95 evidence |
| 5 | [Targeted Mutations And Delta Responses](./phase-05-targeted-mutations-and-delta-responses.md) | Completed except staging p95 evidence |
| 6 | [Mobile Stale-While-Revalidate](./phase-06-mobile-stale-while-revalidate.md) | Completed |
| 7 | [Performance Rollout And Documentation](./phase-07-performance-rollout-and-documentation.md) | Completed locally except staging p95 evidence |

## Dependencies

- Design source: [approved brainstorm](../reports/brainstorm-260720-0205-recommendation-performance-redesign.md).
- Related unfinished plan: `../260716-1509-four-table-meal-catalog-rework/`. Its implementation exists on `delivery`, but phases 3-6 remain open; resolve shared-file ownership before executing phases 2-5 here rather than rewriting the older plan's status.
- Dependency graph: 1 -> {2,3,4}; 2 -> 5; {2,5} -> 6; {3,4,5,6} -> 7.

## Performance Gates

- Active compact-plan read p95 <300 ms; swap/log changed-slot response p95 <300 ms.
- Warm generation p95 <500 ms; cold refresh plus generation p95 <1,000 ms.
- Warm generation performs zero full-catalog SQL; swap/log perform no full-plan hydration.
- Catalog sizes 180, 1,000, and 5,000 preserve deterministic selections and alternatives.

## Red Team Review

- Contract drift is contained by changing the unreleased backend and mobile feature together and locking one final HTTP contract.
- Staleness is contained by revision checks, bounded TTL, single-flight refresh, and last-good fallback.
- Every compact/detail/mutation query authorizes through the owner anchor.
- Unit CI gates call counts, SQL shape, payload ratio, and injected clocks; absolute p95 runs only on a pinned runner or staging.
- Fixed: fresh create and replay explicitly avoid the repository's current post-save/full-plan hydration.
- Fixed: aggregate-affinity parity caps each item before bucket aggregation, not the grouped total.

## Validation Log

- Backend, mobile, and test inventories independently reviewed against live code.
- All seven phases use tests-before/refactor/tests-after gates and exact file ownership.
- Unresolved contradictions: 0.
- Phase 1 completed with characterization-only tests and baseline evidence at `plans/reports/meal-recommendation-performance-baseline.json`.
- Phases 2-6 implemented compact/detail/delta backend contracts, process-local catalog snapshots, aggregate affinity, targeted mutations, and mobile stale-while-revalidate.
- Final local benchmark evidence generated at `plans/reports/meal-recommendation-performance-final.json`; staging p95 gates remain pending.

## Unresolved Questions

- None.
