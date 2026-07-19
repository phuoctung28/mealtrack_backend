---
phase: 3
title: "Immutable Curated Recipe Catalog"
status: in_progress
priority: P1
effort: "7-10d"
dependencies: [2]
---

# Phase 3: Immutable Curated Recipe Catalog

## Overview

Create stable recipe identities, immutable published versions, normalized ingredients/meal types, provenance, and a reproducible seed pipeline.

## Context Links

- [Plan](./plan.md)
- Architecture source: `/Users/alexnguyen/Downloads/nutree_meal_recommendation_mvp_architecture.md` sections 6, 24, 26

## Key Insights

- `food_reference` is ingredient nutrition authority, not a recipe catalog.
- Existing `scripts/import_food_seeds.py` is stale; catalog availability is not reproducible today.

## Requirements

- Functional: exactly 180 commissioned initial recipes (60 Vietnamese, 60 Japanese, 60 Korean); breakfast/lunch/dinner eligibility; immutable versions; normalized ingredients; approved rights record; dry-run/idempotent import.
- Non-functional: publish-time macro derivation and sufficient meal-type coverage within each cuisine. TheMealDB/CC sources are supplemental only after separate approval.

## Architecture

Tables: `catalog_releases`, `catalog_recipes`, `catalog_recipe_versions`, `catalog_recipe_version_meal_types`, `catalog_recipe_ingredients`, `catalog_recipe_sources`, `catalog_recipe_rights_records`. Each publishable version has an approved rights record. Version ingredients snapshot resolved grams, macros, serving/density inputs, and source revision while retaining `food_reference_id` as lineage.

## Related Code Files

- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/migrations/versions/<timestamp>_add_catalog_recipe_tables.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/model/meal_recommendation/catalog_recipe.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/ports/catalog_recipe_repository_port.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/database/models/meal_recommendation/`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/catalog_recipe_repository_async.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/database/models/__init__.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/database/uow_async.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/scripts/import_catalog_recipe_seeds.py`
- Pending content handoff: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/scripts/data/meal-recommendation-recipes.json`

## Implementation Steps

1. Write PostgreSQL timestamped migration with checks, unique keys, indexes, release activation, and database-enforced rejection of published-version update/delete.
2. Add domain values, ORM models, explicit mappers, typed repository, UoW port/concrete registration.
3. Product/Content Acquisition delivers the commissioned corpus. Founder/CEO or authorized signatory, advised by IP counsel, approves rights. Define version-controlled schema for content, images, rights agreement identifier/status, attribution, and approval metadata.
4. Implement manifest digest, bounded schema, source allowlist, reviewer/publisher authorization, change report, append-only import audit, and staged idempotent import; import never auto-publishes or deletes.
5. Compute version macros from resolved grams and reject unresolved nutritional ingredients.
6. Validate digest and segment/unique coverage in the target DB, then atomically activate the release; retain one-step rollback to the prior release. Identical content is a no-op; changed content creates a new version ID.
7. Add production pre-deploy import/verification command beside Alembic; feature enablement fails closed unless the expected release is active.

## Todo

- [x] Migration head remains single.
- [x] Published versions are immutable and reproducible.
- [ ] Partial imports are invisible; prior release remains active on any failure.
- [x] Catalog seed and rights checks pass for schema/sample validation.

## Success Criteria

- [ ] Catalog release gate produces 9-slot-capable eligible pools and five-alternative capacity.
- [x] Migration, repository integration, import dry-run, and architecture tests pass.

## Implementation Log

### 2026-07-16

- Added PostgreSQL catalog release, recipe, immutable version, meal-type, ingredient, source, and rights-record tables with checks, indexes, single active-release enforcement, and published-version mutation triggers.
- Added catalog recipe domain projections, repository port, async repository, ORM models, and UoW registration for active published recipe projections.
- Added catalog seed manifest validator and dry-run CLI. Production defaults require 180 recipes and minimum cuisine/meal-type coverage; sample fixture thresholds pass only when explicitly requested.
- Verified focused Phase 3 tests, Alembic single-head graph, Ruff, and import-linter.
- Blocker: the real commissioned 180-recipe corpus and production DB import/activation path are not present in the repo, so final release activation remains pending.

## Risk Assessment

Thin/invalid catalog yields repetitive or unsafe nutrition. Mitigation: strict publication and launch coverage gates.

## Security Considerations

Allowlisted source/image URLs; provenance and hosting permission required; seed artifact is digest-pinned, reviewed, audited, validated, and bounded.

## Next Steps

- Finish production import/activation after the commissioned 180-recipe corpus and rights records are available. Phase 4 may build deterministic ranking against the active published projection contract, but real 9-slot capacity remains blocked until content lands.

## Unresolved Questions

- Where is the approved 180-recipe commissioned corpus and rights manifest that should become `scripts/data/meal-recommendation-recipes.json`?
