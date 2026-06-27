---
type: brainstorm-report
date: 260627-1322
status: approved
topic: meal scan prompt and beverage simplification
---

# Meal Scan Prompt And Beverage Simplification

## Summary

Approved direction: rework meal image scan so the prompt has one clean contract:
analyze visible edible or drinkable intake as meal nutrition. Remove packaged
beverage special routing from meal scan. Hydration remains explicit through
`/v1/hydration/*`.

## Problem

The current meal scan prompt does two jobs:

- normal meal nutrition analysis
- packaged beverage detection for hydration-only routing

This creates semantic noise. A meal scan can return `is_food=false` for drinks
while still carrying `beverage_metadata`, and the handlers then bypass the
normal meal path. That makes prompt behavior harder to reason about and can
interact badly with food-guard decisions for ambiguous real food images.

## Requirements

- `/v1/meals/image/analyze` treats caloric beverages as normal scanned meals.
- `/v1/meals/scan-by-url` does the same.
- No meal-scan path creates `hydration_entries`.
- Prompt remains stable and cache-friendly: one static system prompt for
  `meal_scan`; dynamic details stay in the user message.
- True non-food still rejects with existing `NOT_FOOD_IMAGE` behavior.
- Zero-cal hydration drinks should not create meal rows from this flow in the
  first implementation pass.

## Evaluated Approaches

### A. Keep beverage special routing and patch prompt wording

Pros:
- smallest code change
- preserves current hydration scan behavior

Cons:
- keeps two mental models in one prompt
- still requires model to say packaged drinks are not food
- likely source of future ambiguous false negatives

Verdict: reject.

### B. Remove beverage routing from meal scan

Pros:
- meal scan has one job
- simpler prompt and response semantics
- caloric drinks naturally count in meal macros
- no transient meal-shaped hydration responses

Cons:
- removes scan-to-hydration feature from meal endpoints
- docs/tests must change
- hydration users must use hydration endpoints for water/zero-cal drinks

Verdict: approved.

### C. Add separate beverage scan endpoint later

Pros:
- clean product surface if hydration scanning is still desired
- prompt can specialize for label reading without disturbing meal scan

Cons:
- extra endpoint/mobile work
- not needed for immediate false-negative fix

Verdict: defer.

## Recommended Solution

Implement approach B.

Prompt contract:

- `is_food=true` means the image contains a visible edible or drinkable item
  intended for intake.
- Ambiguous but likely edible images return `is_food=true` with lower
  confidence, not rejection.
- Caloric drinks are returned as normal `foods` entries.
- Packaged beverage metadata is not requested for meal scan.
- Use canonical macro keys in examples: `protein_g`, `carbs_g`, `fat_g`,
  `fiber_g`, `sugar_g`.

Handler contract:

- Remove upload and scan-by-url beverage branches.
- Always pass successful `is_food=true` output through the normal nutrition
  parser and meal persistence path.
- Keep `has_food` guard for empty/zero-cal invalid output.

## Risks

- Existing mobile behavior may expect scanned Coke to appear in hydration.
  Need confirm mobile UI path before release.
- Existing docs say beverage scan is hydration-only; must update or mark
  deprecated.
- Zero-cal drinks need explicit product decision. Recommended first pass:
  reject via existing calories guard and keep hydration logging explicit.

## Validation

- Existing pastry image returns food, not non-food.
- Caloric packaged drink returns normal meal.
- Water/zero-cal drink does not create hydration entry from meal scan.
- Laptop/shoe/person still returns `NOT_FOOD_IMAGE`.
- Upload and scan-by-url have matching behavior.
- Prompt cache metrics still report stable `meal_scan` cache key reuse.

## Next Steps

Create implementation plan with TDD-style phases because this changes a
behavior contract and has existing tests/docs to unwind.

## Unresolved Questions

None for the approved first pass. Separate beverage-specific scan can be
revisited later.
