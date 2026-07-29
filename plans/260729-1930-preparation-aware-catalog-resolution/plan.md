---
title: "Preparation-aware catalog ingredient resolution"
description: "Resolve the bootstrap catalog corpus without allowing raw/cooked or unverified food-reference matches to silently alter nutrition."
status: pending
priority: P2
branch: "codex/fix-partial-catalog-cuisine-validation"
tags: [catalog, food-reference, resolver, nutrition-safety]
blockedBy: []
blocks: [260716-1509-four-table-meal-catalog-rework]
created: "2026-07-29T12:37:41.730Z"
createdBy: "ck:plan"
source: skill
---

# Preparation-aware catalog ingredient resolution

## Overview

The 100-recipe bootstrap manifest has 528 ingredient occurrences, 158 unique
ingredient names, and no assigned `food_reference_id`. Import remains
fail-closed: a recipe with any unresolved ingredient is not inserted. This
plan adds a preparation-aware resolver workflow and a reviewed mapping process;
it does not permit partial recipes or derive calories outside the backend.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Resolve corpus](./phase-01-resolve-corpus.md) | Pending |
| 2 | [Implement resolver safeguards](./phase-02-implement-resolver-safeguards.md) | Pending |
| 3 | [Verify import](./phase-03-verify-import.md) | Pending |

## Dependencies

- Unblocks the approved-corpus import gate in
  `../260716-1509-four-table-meal-catalog-rework/`.
- Requires an authorized reviewer for nutrition identity decisions and the
  current `food_reference` data set for dry-run evidence.

## Resolution Policy

| Result | Rule | Import action |
| --- | --- | --- |
| Auto-resolved | Verified candidate, preparation-compatible, score at least 0.90, and at least 0.08 ahead of runner-up | Include ingredient |
| Review suggestion | Verified candidate with score 0.80-0.89, or an approved name needing human confirmation | Require resolver-map decision |
| Unresolved | Score below 0.80, preparation mismatch, missing canonical food, or unverified candidate | Withhold recipe; never omit ingredient |

## Success Criteria

- All 158 unique manifest ingredient names are resolved, explicitly rejected,
  or backed by a documented missing-food task.
- A catalog import never writes a recipe missing an ingredient.
- Raw/cooked/fried/grilled wording cannot silently collapse to the same mapping.
- Dry-run and replay evidence show deterministic mappings and backend-derived nutrition.
