---
phase: 3
title: "Verify import"
status: pending
priority: P1
effort: "1d"
dependencies: [1, 2]
effort: ""
---

# Phase 3: Verify import

## Overview

Prove the reviewed corpus can be resolved, imported, and replayed without
silently changing recipe composition or nutrition identity.

## Requirements

- Use the admin `/resolve` endpoint before `/import`.
- Validate with `partial: true` for the 100-recipe bootstrap corpus.
- Do not enable `resolve_all_best_effort` for the acceptance run.

## Related Code Files

- Read: `docs/meal-catalog-import-schema.md`
- Test: `tests/unit/domain/services/meal_recommendation/test_catalog_recipe_seed_validator.py`
- Test: `tests/integration/postgres/test_catalog_import_flow.py`

## Implementation Steps

1. Run resolver dry-run with the approved resolver map and save the report.
2. Require zero unresolved issues, zero review-required duplicates, and only
   verified food references before import.
3. Import to a non-production database and replay the same manifest.
4. Confirm first run inserts complete recipes and replay inserts zero rows.
5. Promote only the reviewed mapping artifact and evidence; keep bootstrap
   best-effort mode out of production procedure.

## Success Criteria

- [ ] Resolver dry-run has no unresolved ingredient issues.
- [ ] Every imported recipe retains all declared ingredients.
- [ ] Replay is idempotent and nutrition remains backend-derived.
