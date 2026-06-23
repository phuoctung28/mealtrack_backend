---
phase: 1
title: "Schema Contract"
status: pending
priority: P1
effort: "0.5 day"
dependencies: []
---

# Phase 1: Schema Contract

## Overview

Lock the exact structured response contract before touching provider or retry code. Current `VisionAnalyzeResponse` validates foods/macros, but it omits `emoji`, `total_calories`, and per-food `calories` that the prompt asks for. That mismatch makes provider-native structured output harder and leaves raw-parser failures looking like model failures.

## Context Links

- `src/domain/parsers/vision_response_models.py`
- `src/domain/services/prompts/system_prompts.py`
- `src/domain/parsers/gpt_response_parser.py`
- `tests/unit/domain/parsers/test_vision_response_models.py`
- LangChain Google GenAI structured output docs
- Gemini structured output docs

## Key Insights

- The model prompt requires `dish_name`, `emoji`, `foods`, `total_calories`, and `confidence`.
- Existing schema only covers `dish_name`, `foods`, and `confidence`.
- Backend calories remain source of truth. AI-provided calories can be accepted as optional evidence, but backend macro-derived calories remain the persisted/displayed truth.
- `gpt_response_parser.py` currently consumes `structured_data`; provider output should normalize into that existing shape instead of changing the API route contract.

## Requirements

- Functional: schema must represent the full current prompt response shape.
- Functional: zero or invalid quantity foods stay handled by existing validation policy.
- Functional: normalized provider output must still feed the existing `parse_foods_from_response()` path.
- Non-functional: schema must be Pydantic v2 compatible and usable by LangChain `with_structured_output`.
- Non-functional: no API response shape change.

## Architecture

The schema lives in the domain parser layer because it describes the provider-independent AI contract. Infrastructure providers can import it for validation, but domain must not import LangChain or provider packages.

## Related Code Files

- Modify: `src/domain/parsers/vision_response_models.py`
- Modify: `tests/unit/domain/parsers/test_vision_response_models.py`
- Read: `src/domain/parsers/gpt_response_parser.py`
- Read: `src/domain/services/prompts/system_prompts.py`

## Implementation Steps

### Tests Before

1. Add schema tests for a complete meal scan payload with `emoji`, `total_calories`, per-food `calories`, and nested macros.
2. Add a compatibility test for older payloads if current parser paths still tolerate missing optional fields.
3. Add a zero-quantity food test to prove existing sanitizer remains intact.

### Refactor

1. Extend `FoodItemResponse` with optional or required `calories` based on downstream parser expectations.
2. Extend `VisionAnalyzeResponse` with `emoji` and `total_calories`.
3. Add a small normalization helper or method only if it keeps provider code from duplicating schema-to-dict behavior.
4. Add field descriptions that help provider-native schema generation.
5. Keep constraints realistic: `confidence` between 0 and 1 if adding bounds does not break current fixtures.
6. Keep AI calories optional or advisory if required fields would break current fallback providers.

### Tests After

1. Run domain parser tests.
2. Run focused GPT parser tests if they consume these fields.
3. Confirm `model_json_schema()` is serializable.

## Todo List

- [ ] Decide required vs optional for `emoji`, `total_calories`, and item `calories` based on parser compatibility.
- [ ] Add complete-response schema tests.
- [ ] Update schema.
- [ ] Verify serialization.

## Success Criteria

- [ ] `VisionAnalyzeResponse.model_json_schema()` includes every prompt-required field.
- [ ] Provider-normalized output can still be wrapped as `{"structured_data": ...}` for existing parser/service code.
- [ ] Existing valid vision payload tests still pass.
- [ ] No provider or API files changed in this phase.

## Risk Assessment

Risk: making fields required can break fallback responses from older providers. Mitigation: start with optional fields if current downstream parsers tolerate absent values, then tighten only after regression data.

## Security Considerations

No new user input or secret handling. Do not add raw image, prompt, or raw AI response logging in tests or schema errors.
