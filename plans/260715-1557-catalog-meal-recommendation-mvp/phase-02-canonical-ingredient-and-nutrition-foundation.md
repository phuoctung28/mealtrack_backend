---
phase: 2
title: "Canonical Ingredient And Nutrition Foundation"
status: complete
priority: P1
effort: "3-5d"
dependencies: [1]
---

# Phase 2: Canonical Ingredient And Nutrition Foundation

## Overview

Make `food_reference` identity survive all meal flows and add strict recipe quantity-to-gram resolution.

## Context Links

- [Plan](./plan.md)
- [Codebase scout](../reports/scout-260715-meal-recommendation-codebase.md)

## Key Insights

- DB column exists, but domain, mapper, edit, API, and suggestion-save paths drop `food_reference_id`.
- Serving rows may have neither grams nor milliliters; unknown conversions must fail publication, never default silently.

## Requirements

- Functional: preserve canonical ID on read/write/edit/log; resolve quantity/unit through food-specific conversions; allow explicitly display-only garnish.
- Non-functional: calories remain `P*4 + (C-fiber)*4 + fiber*2 + F*9`; no second ingredient authority.

## Architecture

Extend the existing nutrition domain and mapper. Add a pure conversion service consuming a typed food-reference projection; infrastructure supplies normalized aliases/servings.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/model/nutrition/nutrition.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/mappers/meal_mapper.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/mappers/meal_mapper.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/strategies/meal_edit_strategies.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/meal_suggestion/save_meal_suggestion_command_handler.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_recommendation/ingredient_quantity_conversion_service.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/ports/food_reference_repository_port.py`

## Implementation Steps

1. Add nullable `food_reference_id` to domain `FoodItem`, serialization, API mapping, ORM mapping, and all reconstruction paths.
2. Add round-trip/update tests proving the existing FK survives create, read, edit, and suggestion-to-meal save.
3. Define alias normalization and typed serving projections; publication accepts only `is_verified=true` references from an approved source and rejects null/ambiguous conversions, incomplete macros, and implausible serving/density values.
4. Implement pure gram resolution for grams, milliliters via density, and named food-specific servings.
5. Add macro scaling and derived-calorie boundary tests; no DB migration for the existing food-item FK.

## Todo

- [x] Canonical ID round-trips through all active meal paths.
- [x] Quantity conversion rejects unsafe inputs.
- [x] Unverified or unapproved-source foods cannot enter a published recipe.
- [x] Layer boundary remains clean.

## Success Criteria

- [x] Food-reference projection/repository tests plus new round-trip/conversion tests passes.
- [x] Targeted Ruff checks pass.
- [x] `.venv/bin/lint-imports` passes.

## Implementation Log

### 2026-07-16

- Added nullable `food_reference_id` to the domain `FoodItem`, dictionary serialization, API request/response schema path, API mapper path, ORM mapper path, meal suggestion save command, and suggestion-save handler materialization.
- Preserved `food_reference_id` through normal meal edit reconstruction for custom nutrition updates, unit-change refreshes, and simple quantity scaling.
- Added tests for route command plumbing, ORM/domain round-trip, detailed response serialization, edit reconstruction, and suggestion-save handler direct/proportional macro materialization.

### 2026-07-16 Completion

- Added a pure `IngredientQuantityConversionService` that resolves grams, metric weight, metric volume through validated density, and named food-specific servings.
- Added typed food-reference nutrition and serving projections behind a domain port, with async repository support for loading normalized serving rows and legacy JSON servings.
- Enforced fail-closed publication rules for unverified or unapproved references, missing macros, implausible macro snapshots, ambiguous servings, invalid density, invalid quantities, unknown units, oversized resolved grams, and fiber/sugar values that exceed carbs.
- Preserved `food_reference_id` through meal-suggestion domain responses, recipe generation scaling, Redis nutrition lookup cache, suggestion response mapping, and suggestion save into normal meal logging.
- Updated save fallback calories to use the backend fiber-aware macro formula.
- Validation passed: 144 targeted unit tests, touched-file Ruff, `.venv/bin/lint-imports`, and `git diff --check`.

## Risk Assessment

Mapper omissions can silently erase identity. Mitigation: explicit round-trip and edit-recreate regression tests.

## Security Considerations

Validate numeric bounds and units; do not expose internal provenance or infer allergy safety.

## Next Steps

- Phase 3 may now build the immutable curated recipe catalog on top of this proven conversion contract.
