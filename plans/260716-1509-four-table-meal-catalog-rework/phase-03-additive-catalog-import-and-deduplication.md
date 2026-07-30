---
phase: 3
title: "Additive Catalog Import And Deduplication"
status: pending
priority: P1
effort: "2-3d"
dependencies: [2]
mode: tdd
---

# Phase 3: Additive Catalog Import And Deduplication

## Overview

Implement strict additive-only import for the initial 180 meals with deterministic exact and review-only near-duplicate detection.

## Requirements

- SHA-256 canonical payload version `meal_catalog_content_v1`.
- Normalize text with Unicode NFKC, trim, whitespace collapse, casefold; serialize grams as fixed-point Decimal.
- Hash cuisine, normalized name, eligibility, ordered `(food_reference_id, resolved_grams)`, and ordered normalized instructions.
- Existing `catalog_key` rejects; existing `content_hash` skips; near matches withhold for review; no automatic update/delete/merge.
- One transaction, advisory import lock, batch ingredient lookup, deterministic report.

## File Inventory

| Action | Files |
|---|---|
| Rewrite | `src/domain/services/meal_recommendation/catalog_recipe_seed_validator.py` |
| Rewrite | `scripts/import_catalog_recipe_seeds.py` |
| Rewrite | `src/domain/ports/catalog_recipe_repository_port.py`, `src/infra/repositories/catalog_recipe_repository_async.py` |
| Modify | `src/domain/ports/async_unit_of_work_port.py`, `src/infra/database/uow_async.py` |
| Rewrite tests | `tests/unit/domain/services/meal_recommendation/test_catalog_recipe_seed_validator.py`, `tests/unit/infra/repositories/test_catalog_recipe_repository_async.py` |

## Tests Before

1. Hash invariance: Unicode form, case, whitespace, decimal formatting, JSON key order.
2. Hash sensitivity: cuisine/name/eligibility/ingredient ID/grams/order/instruction/order.
3. Same-file and DB duplicate key/hash classification; deterministic report ordering.
4. Unresolved ingredient or invalid input produces zero writes; replay produces zero inserts.

## Refactor

1. Remove release/source/rights/version manifest requirements.
2. Resolve ingredients in one batch through `food_reference`; reject ambiguous/unverified inputs according to existing validator policy.
3. Compute exact hashes and report possible duplicates using same normalized name+cuisine plus ingredient-signature similarity.
4. Treat similarity thresholds as named, tested policy; report only and require explicit review approval.
5. Under one transaction advisory lock, recheck keys/hashes, insert ready parents/children, flush, then commit at UoW boundary.
6. CLI supports dry-run and import; output imported/skipped/rejected/review-required counts and stable item lists.

## Tests After And Regression Gate

`.venv/bin/python3.13 -m pytest -q tests/unit/domain/services/meal_recommendation/test_catalog_recipe_seed_validator.py tests/unit/infra/repositories/test_catalog_recipe_repository_async.py tests/unit/infra/repositories/test_food_reference_repository_async.py`

## Success Criteria

- [ ] Identical re-import inserts zero rows.
- [ ] Exact duplicates cannot bypass DB constraints under concurrency.
- [ ] Near duplicates never auto-merge or auto-insert.
- [ ] Valid ready rows and ingredients commit atomically.

## Risks And Security

False-positive fuzzy matches delay content but do not corrupt it. Bound file size/field lengths and never log full meal payloads.

## Next Steps

Use active `meal_catalog` rows directly in deterministic recommendation generation.
