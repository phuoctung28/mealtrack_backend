---
phase: 1
title: "Resolve corpus"
status: pending
priority: P1
effort: "1d"
dependencies: []
effort: ""
---

# Phase 1: Resolve corpus

## Overview

Build one reviewed decision set for the 158 unique ingredient names in the
100-recipe bootstrap manifest. Do not resolve each repeated occurrence
independently.

## Requirements

- Run `/resolve` with `partial: true` and a 0.85 reporting threshold.
- Group results by source ingredient name and preparation state, not the legacy
  qualifier-stripped normalized name alone.
- Classify candidates as safe, review, preparation mismatch, unverified exact,
  or missing canonical food.

## Related Code Files

- Read: `src/app/services/catalog_meal_seed_import_service.py`
- Read: `src/domain/services/meal_suggestion/ingredient_name_normalizer.py`
- Input: `/Users/alexnguyen/Downloads/meal-recommendation-recipes-english-generic-cuisines.json`
- Output: reviewed resolver-map artifact in approved catalog storage

## Implementation Steps

1. Extract distinct ingredient names and occurrence counts from the manifest.
2. Request a non-mutating resolver report with candidate IDs, scores, sources,
   and verification state.
3. Review one decision per distinct ingredient: map to a verified canonical row,
   create/verify a missing canonical row, or reject the recipe content.
4. Record approved mappings with source name, preparation state, canonical ID,
   reviewer, and rationale.

## Success Criteria

- [ ] Every repeated ingredient reuses one reviewed decision.
- [ ] No resolver-map entry points at an unverified or nutritionally
  incompatible food reference.
- [ ] The report distinguishes a missing food from an ambiguous match.
