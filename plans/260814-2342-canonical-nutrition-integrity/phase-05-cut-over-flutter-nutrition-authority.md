---
phase: 5
title: "Cut Over Flutter Nutrition Authority"
status: pending
effort: 3d
---

# Phase 5: Cut Over Flutter Nutrition Authority

## Context Links

- [Flutter contract research](./research/flutter-contract-and-preview.md)
- Flutter `lib/features/meal_creation/data/models/food_search_models.dart`
- Flutter `lib/features/meal_creation/domain/entities/food_item.dart`
- Flutter `lib/features/meal_creation/domain/entities/cart_food_item.dart`
- Flutter `lib/features/meal_creation/domain/services/food_item_calculator.dart`
- Flutter `lib/features/meal_creation/application/services/manual_meal_save_mapper.dart`
- Flutter meal-edit source-nutrition models and repository

## Overview

Priority P1. Preserve backend source identity and calorie density across search/parse/barcode -> draft/cart -> save/cache -> edit. Flutter may calculate grams and proportionally scale each backend value; it never derives calories from macros. Food-label and explicit user overrides are displayed only when supplied/validated by backend.

## Key Insights

- Current creation models drop `food_reference_id`; `FoodItem` ignores supplied calories and derives them.
- `CartFoodItem.fromFoodItem()` clears the calorie override, propagating the second calorie engine.
- Meal edit already carries `foodReferenceId` and `sourceNutrition`; creation should reuse that model pattern.
- Parse UI, barcode save, shared nutrition models, and parsed-edit models contain additional active formula/override paths beyond the original meal-creation entities.

## Requirements And Architecture

- Carry origin, `caloriesPer100g`, per-100g macros, and normalized units through every creation/edit layer.
- Portion preview: `total = backend_per_100g * total_grams / 100` independently for calories and each macro.
- Structured request sends identity + quantity/unit, not `custom_nutrition` or authoritative `allowed_units`; explicit custom remains separate. Flutter serving metadata is display/preview state only.
- Successful backend response reconciles draft/cart/cache before navigation or summary rendering.
- Parse old and additive backend payloads during rollout; do not invent missing authority values.
- Explicit custom items obtain backend calorie density from the v2 preview before calorie display; no Flutter macro-to-calorie formula remains.
- For v2 structured saves, `200` with null `meal_detail` is a protocol failure: fetch meal detail by ID before marking the cache synced/navigation. Never seed a synced cache from draft nutrition.
- Honor the Phase 4 action matrix: add/source replacement sends origin; quantity/unit update inherits source; remove sends ID only; override sends explicit user intent; parser/barcode code never fabricates an override.
- Reuse one stable `Idempotency-Key` for retries and enable v2 only after durable-write capability advertises create/edit support. Handle 409/429/503 without changing the key or creating a second optimistic meal.
- Send contract/app/platform headers on every v2 preview/create/edit request and keep body/header contract versions identical.
- Barcode logging preserves backend `food_reference_id`, source nutrition, and backend calorie/food-label override; it does not flatten the product into custom macros.

## Related Code Files

Flutter modify:

- `lib/features/meal_creation/data/models/food_search_models.dart`
- `lib/features/meal_creation/data/models/parse_text_models.dart`
- `lib/features/meal_creation/data/models/manual_meal_models.dart`
- `lib/features/meal_creation/data/models/manual_meal_response.dart`
- `lib/features/meal_creation/data/repositories/food_repository.dart`
- `lib/features/meal_creation/domain/entities/food_search_result.dart`
- `lib/features/meal_creation/domain/entities/food_item.dart`
- `lib/features/meal_creation/domain/entities/cart_food_item.dart`
- `lib/features/meal_creation/domain/services/food_item_calculator.dart`
- `lib/features/meal_creation/application/providers/ai_meal_parser_provider.dart`
- `lib/features/meal_creation/application/services/manual_meal_save_mapper.dart`
- `lib/features/meal_creation/application/services/manual_meal_save_service.dart`
- `lib/features/meal_creation/application/services/manual_meal_local_cache_writer.dart`
- `lib/features/meal_creation/application/providers/meal_creation_provider.dart`
- `lib/features/meal_creation/presentation/widgets/ai_prompt_section.dart`
- `lib/features/meal_creation/presentation/screens/create_meal_screen.dart`
- `lib/features/meal_creation/presentation/widgets/portion_config_bottom_sheet.dart`
- `lib/features/meal_edit/presentation/widgets/food_search_results.dart`
- `lib/features/meal_edit/presentation/widgets/parsed_food_results_list.dart`
- `lib/features/meal_edit/data/models/food_item_change_request_model.dart`
- `lib/features/meal_edit/data/models/editable_food_item_model.dart`
- `lib/features/meal_edit/data/models/manual_nutrition_override_model.dart`
- `lib/features/meal_edit/data/models/meal_edit_request_model.dart`
- `lib/features/meal_edit/data/repositories/meal_edit_repository.dart`
- `lib/features/meal_edit/domain/entities/edit_request_builder.dart`
- `lib/features/meal_edit/domain/entities/editable_meal_details.dart`
- `lib/features/meal_edit/application/providers/meal_edit_providers.dart`
- `lib/features/meal_edit/presentation/widgets/custom_ingredient_form.dart`
- `lib/features/meal_edit/presentation/widgets/compact_macro_badges.dart`
- `lib/features/meal_edit/presentation/controllers/ingredient_editor_state_mixin.dart`
- `lib/features/meal_edit/presentation/screens/edit_ingredient_screen.dart`
- `lib/features/meal_edit/presentation/controllers/source_measurement_nutrition_cache.dart`
- `lib/features/nutrition_tracking/application/services/meal_detail_cache_writer.dart`
- `lib/features/nutrition_tracking/data/models/meal_cache_model.dart`
- `lib/features/meal_scanner/application/providers/meal_upload_progress_provider.dart`
- `lib/features/barcode_scanner/data/models/barcode_product_response.dart`
- `lib/features/barcode_scanner/domain/entities/scanned_product.dart`
- barcode repository mapper carrying source identity and backend calories
- `lib/core/models/nutrition_models.dart`
- `lib/core/network/durable_write_capability.dart`
- durable-write API/coordinator models used by manual create and edit

Create:

- Flutter focused calculator/mapper/identity tests using existing test layout
- scoped architecture test prohibiting macro-derived calorie/override construction in server-owned search, parse, barcode, save, edit, and cache paths

## TDD Implementation Steps

1. Fetch remote Flutter `delivery`, record its SHA, and create a clean isolated worktree pinned to that SHA. The mobile cutover must track the backend `delivery` line used by this rollout, never Flutter `main` or a stale local branch. Add failing tests for old/new payload parsing, identity survival through search/parse/barcode, `g=1`, labelled 100g serving, and authoritative calorie scaling.
2. Add failing mapper tests proving structured foods omit custom nutrition and explicit custom foods retain it.
3. Add failing create/edit reconciliation tests proving provider/save result replaces preview, post-save feedback, and cache, including `200 + null meal_detail`, detail-refetch failure, and no synced draft-derived fallback.
4. Extend data/domain models and regenerate Freezed/json serialization output; do not hand-edit generated files.
5. Replace macro-derived calorie getters and generated parsed/barcode overrides with backend density/override plus proportional scaling. Use deliberately inconsistent backend-calorie fixtures so tests fail if a formula reappears.
6. Reuse meal-edit source identity and implement Phase 4 action semantics for search, parsed-food, quantity update, source replacement, override/reset, and remove.
7. Route explicit custom preview through backend before displaying calories; barcode uses backend source identity rather than custom macros.
8. Wire capability-gated `Idempotency-Key` for create/edit and test response loss, identical replay, 409 mismatch, 429 backoff, and 503 retry with the same key.
9. Test null detail, stale cache, offline/provider error, rounding, zero/invalid quantity, and repeated edit/save.

## Verification

- `dart run build_runner build --delete-conflicting-outputs`
- `flutter analyze --no-fatal-warnings`
- Focused `flutter test` suites for meal creation and meal edit.
- Scanner/barcode, shared nutrition model, durable-write coordinator, and architecture suites.
- Re-run Phase 4 backend contract suites against the generated Flutter request fixtures.
- Physical-device staging: local and provider search -> portion preview -> save -> Home -> edit -> save.

## Success Criteria

- [ ] No Flutter path derives calories from macros, including explicit custom preview.
- [ ] Canonical/provider identity survives every model and wire boundary.
- [ ] Parse, barcode, edit, shared model, and cache paths cannot synthesize calories or overrides.
- [ ] Preview scales backend calories and macros independently and reconciles from save response.
- [ ] V2 null-detail responses cannot create a synced draft-derived cache entry.
- [ ] Old payloads remain readable during the backend-first release window.

## Risks, Security, And Rollout Gate

- Risks: generated-model drift, stale cache, idempotency mismatch, rounding changes, and mixed app/backend versions. Mitigate with generated diff review, capability gating, stable operation keys, cache reconciliation, adversarial contract fixtures, and backend-first rollout.
- Security: no identity or nutrition payloads added to analytics.
- Gate: additive backend save/edit contract is deployed and healthy. Implementation may finish here, but production app rollout waits for Phase 6 quarantine/constraint evidence.

## Unresolved Questions

None.
