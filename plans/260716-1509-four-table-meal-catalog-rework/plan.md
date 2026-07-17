---
title: "Four-Table Meal Catalog Rework"
description: "Replace the unshipped 12-table catalog recommendation persistence with four tables, additive deduplicated import, outcome learning, and durable operation replay."
status: in_progress
priority: P1
effort: "12-16d"
branch: "codex/catalog-meal-recommendation-mvp"
tags: [refactor, backend, database, api, critical]
blockedBy: []
blocks: [260715-1557-catalog-meal-recommendation-mvp]
created: "2026-07-16T08:09:41.087Z"
createdBy: "ck:plan"
source: skill
mode: deep-tdd
---

# Four-Table Meal Catalog Rework

## Overview

Rework the current feature branch to use `meal_catalog`, `meal_catalog_ingredients`, `meal_recommendations`, and `meal_recommendation_operations`. Preserve route paths, deterministic planning, owner scoping, full operation replay, logging, rollout gating, and the separate AI `/v1/meal-suggestions` flow. Import the team-owned 180 meals additively with exact duplicate prevention and review-only near-duplicate detection.

## Scope Decision

- Selected: scope reduction, deep analysis, tests-first execution.
- Remove: release/version/source/rights/plan/slot/alternative/swap/interaction tables.
- Keep: `food_reference` authority, normal meal materialization, coarse shown/selected/swapped/skipped/logged outcomes, and full request replay through one bounded operation table.
- Defer: recipe mutation history, raw event stream, learned ranking, vector similarity, AI catalog generation.
- Hard gate: never rewrite revisions `20260716000001`-`000003` if any shared database applied them.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Deployment And Regression Gate](./phase-01-deployment-and-regression-gate.md) | In Progress |
| 2 | [Four-Table Schema And Model Collapse](./phase-02-four-table-schema-and-model-collapse.md) | Complete |
| 3 | [Additive Catalog Import And Deduplication](./phase-03-additive-catalog-import-and-deduplication.md) | Pending |
| 4 | [Recommendation Candidate Persistence Rework](./phase-04-recommendation-candidate-persistence-rework.md) | In Progress |
| 5 | [Outcome API Logging And Response Compatibility](./phase-05-outcome-api-logging-and-response-compatibility.md) | In Progress |
| 6 | [Full Verification Rollout And Documentation](./phase-06-full-verification-rollout-and-documentation.md) | Pending |

## Dependencies

- Supersedes `../260715-1557-catalog-meal-recommendation-mvp/` after the deployment gate passes.
- Design source: [approved brainstorm](../reports/brainstorm-260716-1505-four-table-meal-catalog-rework.md).
- Phases execute sequentially; every implementation phase starts with regression tests.
- The 180-meal content file is needed for final import verification, not for schema/refactor work.

## Success Criteria

- Exactly four recommendation feature tables and one Alembic head.
- Re-importing identical content inserts zero rows.
- Exact duplicates are skipped; near duplicates require review and never auto-merge.
- Three-day create/read/swap/skip/log behavior remains owner-scoped and concurrency-safe.
- Calories remain backend-derived from macros; no catalog calorie column.
- Existing `/v1/meal-suggestions` tests remain unchanged and green.

## Red Team Review

- Fixed: batch metadata now lives on one self-referenced anchor row; candidate rows do not repeat it.
- Fixed: exact schema/state constraints, CQRS shown command, caller inventory, and unshipped response-ID migration are explicit in phases.
- Resolved: user approved a fourth operation table, preserving full historical replay and payload-conflict detection.

## Validation Log

- Whole-plan sweep: six phase files reread; old release/version/event persistence appears only as removal or stale-term checks.
- Implementation progress 2026-07-16: four-table migration/model collapse and focused candidate-row API/repository slice are in place; importer, skip/shown command, full live verification, and docs rollout remain.
- Unresolved contradictions: 0.

## Unresolved Questions

- None. User confirmed revisions `20260716000001`-`000003` were never deployed; implementation must still record repository/environment evidence before replacement.
