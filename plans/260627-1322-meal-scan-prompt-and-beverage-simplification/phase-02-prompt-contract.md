# Phase 02 Prompt Contract

## Context Links

- Prompt: `src/domain/services/prompts/system_prompts.py`
- Prompt tests: `tests/unit/domain/services/prompts/test_prompt_constants.py`
- Schema: `src/domain/model/ai/nutrition_contracts.py`
- Parser: `src/domain/parsers/vision_response_parser.py`

## Overview

Priority: high.
Status: completed.

Rewrite the vision prompt so meal scan has one semantic contract and remains
stable for prompt caching.

## Requirements

- Treat visible edible or drinkable intake as food.
- Ambiguous likely edible images return `is_food=true` with lower confidence.
- Caloric beverages are normal `foods` entries.
- Do not request packaged beverage metadata in meal scan.
- Use canonical macro keys in examples.

## Architecture

Keep prompt as static `SystemPrompts.VISION_ANALYSIS`. Do not move dynamic
context into the system prompt because cache keys include the system prompt
hash.

## Related Code Files

- Modify: `src/domain/services/prompts/system_prompts.py`
- Modify: `tests/unit/domain/services/prompts/test_prompt_constants.py`
- Read: `src/infra/services/ai/openai_prompt_cache_policy.py`

## Implementation Steps

1. Remove packaged beverage detection section from meal scan prompt.
2. Replace food guard with a general food-presence policy.
3. Add drink examples as normal food entries if needed.
4. Update examples to canonical macro keys.
5. Adjust prompt tests for the new contract.

## Todo List

- [x] Remove beverage metadata instructions from `VISION_ANALYSIS`.
- [x] Add general edible/drinkable food-presence rule.
- [x] Add lower-confidence ambiguous-food rule.
- [x] Update prompt tests.

## Success Criteria

- Prompt no longer says packaged beverages are `is_food=false`.
- Prompt tests enforce the new semantic contract.
- Prompt remains a static constant shared by all meal scan strategies.

## Risk Assessment

- Removing beverage examples may reduce label-reading accuracy for drinks.
  Accept for this phase because drinks are normal meal items now.

## Security Considerations

- No logging of prompt body, image bytes, or raw provider output.

## Next Steps

Simplify handlers after tests and prompt contract are ready.
