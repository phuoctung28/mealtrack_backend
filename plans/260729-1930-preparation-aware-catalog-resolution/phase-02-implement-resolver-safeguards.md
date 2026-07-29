---
phase: 2
title: "Implement resolver safeguards"
status: pending
priority: P1
effort: "1-2d"
dependencies: [1]
effort: ""
---

# Phase 2: Implement resolver safeguards

## Overview

Make catalog resolution preparation-aware while retaining strict verified-food
requirements and backward-compatible reviewed resolver maps.

## Requirements

- Preserve raw/cooked/fried/grilled state for catalog mapping and candidate
  scoring; do not reuse the qualifier-stripped lookup key as the sole identity.
- Auto-resolve only verified, preparation-compatible candidates at score >=0.90
  with the existing 0.08 runner-up margin.
- Treat 0.80-0.89 as a review suggestion, never an automatic import decision.
- Keep unresolved ingredients as import errors; never drop them from a recipe.

## Related Code Files

- Modify: `src/app/services/catalog_meal_seed_import_service.py`
- Modify: `src/domain/services/meal_suggestion/ingredient_name_normalizer.py`
- Modify: `src/api/schemas/response/admin_meal_catalog_responses.py`
- Modify: `src/api/routes/v1/admin_meal_catalog_import.py`
- Test: `tests/unit/app/services/test_catalog_meal_seed_import_service.py`
- Test: `tests/unit/api/test_admin_meal_catalog_import_route.py`

## Implementation Steps

1. Write failing tests for raw-versus-cooked and exact-but-unverified matches.
2. Add a catalog-specific name/preparation key for resolver-map lookup and
   candidate scoring without changing generic meal-suggestion normalization.
3. Return candidate verification and preparation compatibility in resolver
   reports so the admin UI can present a review decision.
4. Enforce the three resolution bands and retain the 0.08 ambiguity margin.
5. Verify that explicit approved mappings still pass quantity/nutrition safety
   checks before any row is written.

## Success Criteria

- [ ] A cooked ingredient cannot auto-map to a raw candidate solely because
  generic normalization removed its qualifier.
- [ ] An unverified exact candidate remains blocked until verified.
- [ ] The importer reports all unresolved names needed for review and inserts
  no incomplete recipe.
