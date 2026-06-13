---
phase: 2
title: "Canonical AI Nutrition Contracts"
status: completed
effort: "0.5-1d"
---

# Phase 2: Canonical AI Nutrition Contracts

## Context Links

- Current vision schema: `src/domain/parsers/vision_response_models.py`
- Older GPT schema: `src/domain/model/ai/gpt_response.py`
- Existing structured recipe schemas: `src/infra/services/ai/schemas.py`
- Domain nutrition invariant: `src/domain/model/nutrition/nutrition.py`
- Macro calorie derivation: `src/domain/model/nutrition/macros.py`
- Schema tests: `tests/unit/domain/parsers/test_vision_response_models.py`
- Infra schema tests: `tests/unit/infra/services/ai/test_schemas.py`

## Overview

Create one explicit nutrition-output contract family for AI responses. The repo
currently has overlapping schema concepts, and the temporary vision model drops
invalid quantities before validation. This phase defines contracts that reject
bad output instead of repairing it silently.

Priority: P1.

## Requirements

- Add canonical AI nutrition contracts in domain-owned code so application and
  infra can both import them without infra-to-domain cycles.
- Keep task-specific contracts instead of forcing every flow into one shape:
  - `VisionNutritionResponse` for image meal scan.
  - `MealTextNutritionResponse` for natural-language parse.
  - Existing `RecipeDetailsResponse` remains explicit, but tests must prove AI
    nutrition fields are ignored or treated as metadata.
- For vision food estimates, prefer normalized grams:
  - `quantity_g: float = Field(gt=0, le=MAX_FOOD_ITEM_QUANTITY)`.
  - Domain mapping can store `unit="g"`.
- For text parse, preserve display UX:
  - Keep `quantity` and `unit` for user-facing text parse.
  - Add optional `quantity_g` when known.
  - Validate quantity with unit-aware semantic rules in Phase 3.
- Macros use grams and support optional `fiber_g` and `sugar_g`.
- AI-reported calories must not become source-of-truth calories.
- Remove or replace validators that drop invalid foods before validation.

## Architecture

Recommended module:

- `src/domain/model/ai/nutrition_contracts.py`

Recommended models:

- `AINutritionMacros`
- `VisionFoodEstimate`
- `VisionNutritionResponse`
- `MealTextFoodEstimate`
- `MealTextNutritionResponse`
- `AIOutputValidationContext` or equivalent lightweight dataclass if needed by tests

Keep `src/infra/services/ai/schemas.py` for meal suggestion and recipe schemas
unless Phase 4 finds a direct nutrition-flow dependency that benefits from a
small import redirect.

## Related Code Files

Modify:

- `src/domain/model/ai/__init__.py`
- `src/domain/model/ai/gpt_response.py` or stop production imports from it
- `src/domain/parsers/vision_response_models.py` or replace imports with new contracts
- `src/infra/services/ai/schemas.py`
- `tests/unit/domain/parsers/test_vision_response_models.py`
- `tests/unit/infra/services/ai/test_schemas.py`

Create if needed:

- `src/domain/model/ai/nutrition_contracts.py`
- `tests/unit/domain/model/ai/test_nutrition_contracts.py`

## Implementation Steps

1. Write failing tests for `VisionNutritionResponse`:
   - accepts realistic food quantities.
   - rejects `quantity_g=150000`.
   - rejects empty names, negative macros, too many food items.
   - does not include source-of-truth calories.
2. Write failing tests for `MealTextNutritionResponse`:
   - accepts display quantity/unit and optional `quantity_g`.
   - rejects malformed item lists.
   - preserves emoji validation boundary for later handler use.
3. Write recipe-schema regression tests:
   - recipe details can include AI calorie metadata if already supported.
   - downstream deterministic nutrition remains the only source of saved calories.
4. Implement canonical contracts with Pydantic `Field` constraints.
5. Remove pre-validation dropping from the temporary vision schema, or redirect
   callers/tests to the new canonical contract and leave the old module as a
   compatibility shim without silent correction.
6. Export contracts from `src/domain/model/ai/__init__.py`.
7. Run schema-focused tests.

## Success Criteria

- [x] Canonical image and text nutrition contracts exist and are tested.
- [x] `quantity_g=150000` fails contract validation.
- [x] Invalid foods are not silently removed by Pydantic validators.
- [x] AI calories are excluded from domain calorie authority.
- [x] Existing recipe structured-output tests still pass.
- [x] Focused schema tests pass.

## Completion Notes

- Added canonical contracts in `src/domain/model/ai/nutrition_contracts.py`.
- Tightened legacy parser behavior so invalid AI food items fail instead of
  being silently removed.
- Preserved current text-parse compatibility by folding flat macro fields into
  canonical nested macros.
- Reviewer follow-up found no blockers after fixes.
- Validation: focused Phase 1+2 regression suite passed with 110 tests.

## Risk Assessment

- Risk: Contract too strict harms UX. Mitigation: keep text display units and
  move unit-specific plausibility into Phase 3 retry semantics.
- Risk: Duplicate schemas remain. Mitigation: make production imports converge
  during Phase 4 and leave only compatibility shims if needed.

## Security Considerations

- Contracts should constrain list sizes and text lengths to prevent oversized AI
  payloads from flowing deeper into handlers.
- Error messages should identify fields without echoing large raw payloads.

## Next Steps

Proceed to Phase 3 after contracts reject the production failure shape in unit
tests.
