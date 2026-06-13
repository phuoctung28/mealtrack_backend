---
phase: 2
title: "Parser and Prompt Guard"
status: completed
priority: P1
effort: "3h"
dependencies: [1]
---

# Phase 2: Parser and Prompt Guard

## Context Links

- `src/domain/services/prompts/system_prompts.py`
- `src/domain/model/ai/nutrition_contracts.py`
- `src/domain/parsers/vision_response_models.py`
- `src/domain/parsers/gpt_response_parser.py`
- `tests/unit/domain/services/prompts/test_prompt_constants.py`
- `tests/unit/domain/model/ai/test_nutrition_contracts.py`
- `tests/unit/domain/parsers/test_gpt_response_parser.py`
- `tests/unit/domain/parsers/test_vision_response_models.py`

## Overview

Add the domain-level `is_food` response contract and strict parser helper. This phase writes tests first because a naive boolean parse can silently invert `"false"`.

## Key Insights

- Existing parser validates `VisionAnalyzeResponse` before parsing food items.
- `parse_to_nutrition` must continue deriving calories from macros.
- Prompt can ask for provider calories for context, but backend must not consume them as source of truth.

## Requirements

- Functional: `VisionAnalyzeResponse` includes `is_food: bool = True`.
- Functional: `GPTResponseParser.parse_is_food(response) -> bool` returns false only for explicit false values.
- Functional: non-food prompt branch returns a minimal JSON object with no invented dish/food.
- Non-functional: existing real-food responses without `is_food` continue to pass.
- Non-functional: no new parser class or dependency.

## Architecture

`parse_is_food` should read `response["structured_data"]["is_food"]` defensively:

```python
missing -> True
False / "false" / "False" / 0 / "0" -> False
True / "true" / 1 / "1" -> True
other malformed values -> True
```

Prefer explicit helper logic or Pydantic validation; avoid `bool(raw)`.

## Related Code Files

- Modify: `src/domain/services/prompts/system_prompts.py`
- Modify: `src/domain/parsers/vision_response_models.py`
- Modify: `src/domain/parsers/gpt_response_parser.py`
- Modify: `tests/unit/domain/services/prompts/test_prompt_constants.py`
- Modify: `tests/unit/domain/parsers/test_gpt_response_parser.py`
- Modify: `tests/unit/domain/parsers/test_vision_response_models.py`

## Implementation Steps

1. Add failing parser tests:
   - missing `is_food` returns true.
   - boolean false returns false.
   - string `"false"` returns false.
   - numeric `0` returns false.
   - malformed/no `structured_data` returns true.
2. Add failing response-model test proving `is_food` defaults true and accepts false.
3. Add failing prompt test requiring:
   - `"is_food"` in response schema.
   - non-food instruction branch.
   - instruction not to invent food when no edible food is visible.
4. Implement `is_food` on `VisionAnalyzeResponse`.
5. Implement `parse_is_food` in `GPTResponseParser`.
6. Update `VISION_ANALYSIS` response format and guidelines:
   - first field `is_food`.
   - for non-food: `is_food:false`, `dish_name:null`, `emoji:null`, `foods:[]`, `total_calories:0`, low confidence.
   - for food: `is_food:true`, existing structure.
7. Do not parse or trust provider `total_calories`; leave nutrition parsing unchanged except schema compatibility.

## Todo List

- [x] Parser tests fail before implementation.
- [x] Response-model tests fail before implementation.
- [x] Prompt constant tests fail before prompt edit.
- [x] `parse_is_food` handles strings/numbers safely.
- [x] Existing nutrition parser tests still pass.
- [x] Canonical Gemini schema accepts `is_food=false` with empty foods and still rejects empty true-food payloads.

## Success Criteria

- [x] `pytest tests/unit/domain/parsers/test_gpt_response_parser.py tests/unit/domain/parsers/test_vision_response_models.py tests/unit/domain/services/prompts/test_prompt_constants.py -q` passes.
- [x] Missing `is_food` is backward compatible.
- [x] Explicit `is_food:false` never reaches nutrition parsing when handlers use the helper.

## Risk Assessment

- Risk: prompt grows too much and worsens cost/latency. Mitigation: add minimal branch, avoid long examples.
- Risk: strict schema rejects old provider output. Mitigation: default true and keep foods optional as today.
- Risk: calorie-source drift. Mitigation: do not alter `Nutrition` or macro calculation.

## Security Considerations

- Parser tests must not include raw private food payloads.
- Prompt should not request user-identifying data.

## Next Steps

Wire parser helper into command handlers.
