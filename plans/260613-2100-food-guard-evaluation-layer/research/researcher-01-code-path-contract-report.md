---
type: research
plan: food-guard-evaluation-layer
created: 2026-06-13
status: complete
---

# Researcher 01 Report — Code Path Contract

## Scope

Food guard design for meal image analysis. Read-only research. No implementation.

## Findings

- `src/domain/services/prompts/system_prompts.py` owns `SystemPrompts.VISION_ANALYSIS`; all meal-analysis strategies except ingredient identification return it through `src/domain/strategies/meal_analysis_strategy.py`.
- `src/domain/parsers/vision_response_models.py` validates the vision response shape but currently has no `is_food` field.
- `src/domain/parsers/gpt_response_parser.py` parses `structured_data` into `Nutrition`; calories are derived from macros, not provider `total_calories`.
- Active image persistence flows:
  - `UploadMealImageImmediatelyHandler` uploads image, calls vision, parses nutrition, validates `has_food`, then creates the meal.
  - `ScanByUrlCommandHandler` downloads Cloudinary bytes, compresses, calls vision, parses nutrition, validates `has_food`, then creates the meal.
- Registered but legacy image URL command:
  - `AnalyzeMealImageByUrlHandler` is registered in the configured event bus.
  - No route currently references `/v1/meals/image/analyze-url`; old integration tests still mention it.
  - It still uses the same `parse_to_nutrition` then `has_food` path.
- Dead background analysis path:
  - `MealAnalysisEventHandler` exists and subscribes to `MealImageUploadedEvent`.
  - Existing bandwidth plan says this event is never published and should be removed.

## Planning Impact

- Do not add new AI purpose, service, local ML model, DB column, cache, or strategy.
- Add one parser contract and reuse it in all live image command handlers.
- Treat `AnalyzeMealImageByUrlHandler` as legacy-but-registered: either guard it or remove it in a dedicated dead-code plan. For this plan, guard it to avoid a registered unsafe path surviving.
- Do not touch ingredient recognition; its `IngredientIdentificationStrategy` already has a separate non-food/null response contract.

## Open Questions

- None blocking. The plan should state the legacy handler inclusion explicitly.
