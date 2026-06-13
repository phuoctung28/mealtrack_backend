---
phase: 4
title: "Flow Integration And Parser Replacement"
status: pending
effort: "1-2d"
---

# Phase 4: Flow Integration And Parser Replacement

## Context Links

- Immediate upload handler: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Background event handler: `src/app/handlers/event_handlers/meal_analysis_event_handler.py`
- Analyze by URL handler: `src/app/handlers/command_handlers/analyze_meal_image_by_url_command_handler.py`
- Scan by URL handler: `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- Parser: `src/domain/parsers/gpt_response_parser.py`
- Parser tests: `tests/unit/domain/parsers/test_gpt_response_parser.py`
- Upload handler tests: `tests/unit/handlers/command_handlers/`

## Overview

Wire the validated contracts into every meal-analysis flow and remove the
parser-side workaround. The parser becomes deterministic mapping from a
validated AI contract into domain nutrition, not a silent repair engine.

Priority: P1.

## Requirements

- Image flows use `VisionNutritionResponse`:
  - immediate upload.
  - background meal analysis.
  - analyze-by-url.
  - scan-by-url.
- Text parse uses `MealTextNutritionResponse`.
- Recipe generation keeps explicit structured schemas and deterministic
  nutrition calculation.
- Parser no longer drops over-limit foods as final behavior.
- Domain `FoodItem` invariant remains in place as final guard.
- API clients receive controlled errors on repeated invalid AI output.
- Existing successful payload shapes remain compatible where API responses
  already depend on them.

## Architecture

Target image flow:

```text
handler
  -> VisionAIService.analyze_with_strategy
  -> structured schema + validation retry
  -> GPTResponseParser.parse_to_nutrition(validated payload)
  -> Nutrition/FoodItem domain models
  -> persistence/event flow
```

The parser should accept the post-validation shape. If backward compatibility is
needed during migration, support old keys only as a compatibility path with
strict validation, not with silent item deletion.

## Related Code Files

Modify:

- `src/domain/parsers/gpt_response_parser.py`
- `src/domain/parsers/vision_response_models.py`
- `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- `src/app/handlers/event_handlers/meal_analysis_event_handler.py`
- `src/app/handlers/command_handlers/analyze_meal_image_by_url_command_handler.py`
- `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- `tests/unit/domain/parsers/test_gpt_response_parser.py`
- relevant handler tests under `tests/unit/handlers/command_handlers/`

## Implementation Steps

1. Write failing parser regression tests:
   - over-limit quantity raises parsing/validation error instead of being dropped.
   - valid `quantity_g` maps to `FoodItem(quantity=..., unit="g")`.
   - calories still derive from `Macros.total_calories`.
2. Write handler tests for repeated invalid AI output:
   - immediate image upload returns controlled failure.
   - by-url scan/analyze returns controlled failure.
   - background event logs/fails without leaking raw exceptions.
3. Update parser normalization to deterministic mapping only.
4. Remove `_has_supported_quantity` filtering and any Pydantic validator that
   strips invalid foods before field validation.
5. Update image handlers to consume the validated service payload.
6. Update text parse handler to consume `MealTextNutritionResponse` while
   preserving current DTO shape and localization behavior.
7. Confirm recipe pipeline still ignores AI nutrition values and uses
   deterministic lookup/calculation.
8. Run parser, handler, and recipe tests.

## Success Criteria

- [ ] `quantity=150000` or `quantity_g=150000` cannot be saved.
- [ ] Invalid AI output is retried before the parser is reached.
- [ ] Parser does not silently drop invalid items as final behavior.
- [ ] Successful image, text, and recipe flows keep current user-facing behavior.
- [ ] Backend-derived calories remain the only persisted/returned calorie source.
- [ ] Focused parser and handler tests pass.

## Risk Assessment

- Risk: Handler response expectations differ across immediate/background flows.
  Mitigation: test each flow explicitly instead of relying only on parser tests.
- Risk: Backward compatibility path accidentally keeps silent cleanup. Mitigation:
  add a failing test that proves impossible quantity raises after retry failure.
- Risk: Text parse UX regresses by losing localized units. Mitigation: keep text
  display quantity/unit in the text contract and DTO mapping.

## Security Considerations

- User-facing errors should say the analysis needs a clearer photo or more
  context, not expose validation internals.
- Persistence should never receive raw unvalidated AI payloads as trusted domain
  state.

## Next Steps

Proceed to Phase 5 after all production AI nutrition entrypoints use explicit
contracts.
