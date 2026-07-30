---
title: "Meal Recommendation Ranking V2"
description: "Add snapshot-scoped canonical ingredient similarity and bounded plan diversity for new catalog plan generation."
status: in-progress
priority: P1
effort: "6-9d"
branch: "delivery"
tags: [feature, backend, recommendation, ranking, performance, tdd, critical]
blockedBy: []
blocks: []
created: "2026-07-20T14:33:59.032Z"
createdBy: "ck:plan"
source: skill
mode: hard-tdd
---

# Meal Recommendation Ranking V2

## Overview

Update deterministic catalog ranking for new plan generation. Keep all nutrition and catalog eligibility hard, build IDF statistics once per immutable catalog snapshot, use confidence-scaled cosine ingredient similarity, and rerank only a deterministic top-30 shortlist for plan diversity.

The current five endpoints, four recommendation tables, compact/detail/delta responses, aggregate history query, and persisted replay semantics remain unchanged. Distance, stores, maps, location, text ranking, vectors, collaborative filtering, catalog import, and mobile changes are explicitly out of scope.

## Scope Decision

- **HOLD:** implement the user-approved design and weights without expanding the feature boundary.
- Wire the new ranking behavior directly for new plan generation because this branch has not shipped to production.
- Remove algorithm-version branching and keep one deterministic ranking path.
- Existing persisted plans always replay their stored candidates and scores.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Contract And Golden Characterization](./phase-01-contract-and-golden-characterization.md) | Completed |
| 2 | [Snapshot IDF And Normalized Scoring](./phase-02-snapshot-idf-and-normalized-scoring.md) | Completed |
| 3 | [Bounded Diversity And Alternative Ranking](./phase-03-bounded-diversity-and-alternative-ranking.md) | Completed |
| 4 | [Direct V2 Wiring And Performance Verification](./phase-04-versioned-rollout-and-performance-verification.md) | In Progress |

## Dependencies

- Design source: [approved ranking brainstorm](../reports/260720-2112-meal-recommendation-ranking-v2-brainstorm.md).
- Builds on merged catalog recommendation and local performance work in `../260716-1509-four-table-meal-catalog-rework/` and `../260720-0211-meal-recommendation-performance-redesign/`; their remaining documentation/staging evidence does not block implementation.
- Phase order is sequential: 1 locks v1, 2 defines v2 base scoring, 3 adds contextual selection, and 4 wires v2 directly and verifies performance.
- No database migration, API version, or mobile release dependency.

## Success And Performance Gates

- V1 goldens and all five endpoint shapes remain field- and behavior-compatible.
- V2 is deterministic at six-decimal score precision and preserves 9 unique winners plus 45 alternatives.
- IDF uses `ln((N+1)/(df+1))+1`; duplicate ingredients in one meal count once.
- Diversity examines at most 30 eligible candidates per slot and alternatives compare against the other eight winners.
- Warm generation adds no catalog SQL and remains p95 `<500 ms`; read and changed-slot mutation p95 remain `<300 ms`.
- Synthetic 180/1,000/5,000 catalogs show bounded scaling; staging p95 remains a production-promotion gate.
- V1 plans can still replay without mutating or recalculating stored plans.

## Review And Validation

- Hard-mode research checked live ranking, snapshot, handler, persistence, API, analytics, and benchmark seams.
- Independent math/TDD and contract red-team passes completed with no actionable findings.
- Strict ClaudeKit validation completed with 4 phases, 0 errors, and 0 warnings.
- Whole-plan consistency pass found no distance/store/map/schema/endpoint/mobile drift.

## Unresolved Questions

- None. Initial weights are experiment defaults; merge/deploy depends on staging performance and representative quality evidence rather than a runtime rollout mode.
