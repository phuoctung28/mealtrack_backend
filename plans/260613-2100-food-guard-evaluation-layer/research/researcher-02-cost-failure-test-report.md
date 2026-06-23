---
type: research
plan: food-guard-evaluation-layer
created: 2026-06-13
status: complete
---

# Researcher 02 Report — Cost, Failure, Test Risk

## Scope

Validate cost/failure assumptions for single-stage `is_food` guard.

## Findings

- Current Gemini pricing checked on 2026-06-13 from Google AI docs:
  - `gemini-2.5-flash-lite` standard paid tier: $0.10 per 1M text/image/video input tokens, $0.40 per 1M output tokens.
  - `gemini-2.5-flash` fallback: $0.30 per 1M text/image/video input tokens, $2.50 per 1M output tokens.
- `AIModelManager` `MEAL_SCAN` fallback chain is Flash-Lite then Flash. Cost statements must mention fallback can change realized cost.
- Single-stage guard does not save image input tokens. It can save output tokens on junk scans only if prompt strongly tells model to return a small non-food JSON object.
- Existing `has_food` check remains necessary because:
  - Gemini might omit `is_food`.
  - Gemini might return `is_food: true` with empty or zero-calorie foods.
  - Provider JSON recovery may produce partial structured data.
- `parse_is_food` must not use plain `bool(raw_value)`. Strings like `"false"` are truthy in Python.
- Rejected scans should not claim `raw_gpt_json` persistence. Upload and scan-by-url paths do not save a meal after guard rejection.

## Edge Taxonomy

Accept as food:
- Plated meals, snacks, drinks with calories, packaged edible food, raw ingredients, nutrition labels/menu screenshots only if visible edible item or packaged edible product is clear.

Reject as non-food:
- Laptop, shoe, pet, empty plate, kitchen tools, face/body photos, pure packaging with no edible product indication, random object scenes.

Ambiguous:
- Supplements/protein powder, baby formula, medicine-like consumables, unclear menu screenshots. Keep existing `has_food` fallback and prefer user-facing retry over hallucinated nutrition.

## Test Impact

- Add parser tests for missing field, boolean false, string false, numeric false, and malformed/no `structured_data`.
- Add prompt constant tests for `is_food`, non-food branch, and no invented dish.
- Add handler tests proving false guard avoids `parse_to_nutrition`, DB save, translation, and cache invalidation.
- Add route tests proving `ValueError` maps to `NOT_FOOD_IMAGE` and provider outages still map through existing AI unavailable handling.

## Open Questions

- None blocking. Cost numbers are current as of 2026-06-13 and may drift.
