---
type: project-management
plan: plans/260613-1359-llm-nutrition-output-contracts
phase: 2
status: completed
created: "2026-06-13T17:19:00+07:00"
---

# Phase 2 Status: Canonical AI Nutrition Contracts

## Summary

Phase 2 completed. Canonical image/text nutrition contracts exist, legacy parser
item-dropping is removed, and current text parse flat macro output remains
compatible through contract normalization.

## Completed Work

| Area | Result |
|------|--------|
| Canonical contracts | Added `AINutritionMacros`, `VisionNutritionResponse`, `MealTextNutritionResponse` |
| Image validation | Requires non-empty foods; rejects impossible `quantity_g` |
| Text validation | Requires non-empty items; preserves display `quantity`/`unit` |
| Text compatibility | Folds flat `protein/carbs/fat` into canonical nested `macros` |
| Parser behavior | Invalid legacy food quantities now fail instead of partial-save filtering |
| Calorie authority | AI `calories` ignored by nutrition contracts; backend macro-derived calories remain authority |
| Recipe schemas | Existing structured-output schema tests still pass |

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/unit/domain/model/ai/test_nutrition_contracts.py tests/unit/domain/parsers/test_gpt_response_parser.py tests/unit/domain/parsers/test_vision_response_models.py tests/unit/infra/services/ai/test_schemas.py -q` | 65 passed |
| `uv run pytest tests/unit/domain/ports/test_ai_provider_port.py tests/unit/infra/services/ai/test_ai_model_manager.py tests/unit/infra/services/ai/providers/test_gemini_provider.py tests/unit/domain/model/ai/test_nutrition_contracts.py tests/unit/domain/parsers/test_gpt_response_parser.py tests/unit/domain/parsers/test_vision_response_models.py tests/unit/infra/services/ai/test_schemas.py -q` | 110 passed |
| `uv run ruff check` on touched Phase 2 files | passed |
| `uv run mypy` on touched Phase 2 source files | passed |
| `uv run black --check` on touched Phase 2 files | passed |
| `uv run python -m py_compile` on touched Phase 2 source files | passed |

## Review

Initial review flagged runtime partial-save risk because the parser still
filtered invalid foods before validation. Fixed in this phase. Follow-up review
reported no blockers.

## Known Repo-Wide Hygiene

Full-repo checks were attempted for thoroughness but remain blocked by existing
unrelated issues:

| Check | Existing result |
|-------|-----------------|
| `uv run ruff check src tests` | 1924 repo-wide issues |
| `uv run mypy src` | 719 repo-wide errors |
| `uv run black --check src tests` | 171 files would be reformatted |

## Next

Proceed to Phase 3: validation retry orchestration.

## Unresolved Questions

None.
