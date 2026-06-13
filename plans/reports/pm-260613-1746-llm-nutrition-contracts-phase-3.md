# Phase 3 PM Report: LLM Nutrition Output Contracts

## Summary

Phase 3 completed. Invalid structured AI nutrition output now retries exactly
once for meal image scan and text parse flows, then fails through a controlled
`AIOutputValidationError` path. Provider outages remain separate and are not
retried as validation failures.

## Progress

| Area | Status | Notes |
|------|--------|-------|
| Vision meal scan retry | Complete | Uses `VisionNutritionResponse`; invalid nutrition output retries once. |
| Ingredient recognition regression guard | Complete | Keeps unstructured `{name, confidence, category}` contract. |
| Text parse retry | Complete | Uses `MealTextNutritionResponse`; invalid text output retries once. |
| FatSecret divergence guard | Complete | Compares FatSecret calories against backend-derived macro calories. |
| API fallback mapping | Complete | Maps invalid AI output to friendly `AI_OUTPUT_INVALID` without field leaks. |
| Plan sync | Complete | Phase 3 checklist and overview status updated. |

## Validation

| Command | Result |
|---------|--------|
| `uv run pytest tests/unit/infra/adapters/test_vision_ai_service_resilience.py tests/unit/handlers/command_handlers/test_recognize_ingredient_command_handler.py tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py -q` | 21 passed |
| Expanded Phase 1-3 AI boundary pytest slice | 155 passed |
| Touched-file `ruff check` | Passed |
| Touched-source `mypy` | Passed |
| Touched-file `black --check` | Passed |
| Touched-source `py_compile` | Passed |

## Known Baseline

Repo-wide quality commands still have pre-existing unrelated failures:

- `uv run ruff check src tests`
- `uv run mypy src`
- `uv run black --check src tests`

These are not introduced by Phase 3; touched-file checks passed.

## Next

Proceed to Phase 4: flow integration and parser replacement.

## Unresolved Questions

None.
