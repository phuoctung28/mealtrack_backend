---
phase: 1
title: "Dead Code Cleanup"
status: completed
priority: P1
effort: "0.5d"
dependencies: []
---

# Phase 1: Dead Code Cleanup

## Overview

Delete all unreachable code paths and fix cosmetic misnaming. No behavior changes — only dead files, a dead subscription block, and wrong names. Ships as a single focused PR.

> **Red Team fix (F11):** Step order matters. Remove imports and subscribe block from `event_bus.py` BEFORE deleting source files — otherwise the module-level imports crash app startup between steps.
>
> **Red Team fix (F4):** `AnalyzeMealImageByUrl` is registered in `event_bus.py:346-354` and has live unit + integration tests. Delete those tests (or rewrite them against the live path) BEFORE deleting the command/handler.

## Context Links

- Dead event: `src/app/events/meal/meal_image_uploaded_event.py`
- Dead handler: `src/app/handlers/event_handlers/meal_analysis_event_handler.py`
- Dead subscribe block + imports: `src/api/dependencies/event_bus.py:43,121,635-642`
- Command (registered but no live route): `src/app/commands/meal/analyze_meal_image_by_url_command.py`
- Command handler (registered but no live route): `src/app/handlers/command_handlers/analyze_meal_image_by_url_command_handler.py`
- Tests to remove first: `tests/unit/handlers/command_handlers/test_food_guard_command_handlers.py` (imports command/handler), `tests/integration/api/test_meals_api.py:89,114,123,133` (hits `/analyze-url`)
- Adapter with dead method: `src/infra/adapters/vision_ai_service.py` (`analyze_by_url`)
- Strategy with dead method: `src/domain/strategies/meal_analysis_strategy.py` (`_legacy_analysis_prompt`)
- File to rename: `src/domain/parsers/gpt_response_parser.py` → `vision_response_parser.py`
- DI provider referencing old name: `src/api/base_dependencies.py:5,130,137` (`get_gpt_parser()`) ← **must update**
- Eval loop referencing old name: `src/domain/services/meal_analysis/prompt_eval_loop.py:6-30` ← **must update**
- Layer-leak: `src/infra/services/ai/prompts/__init__.py`
- Port docstring fix: `src/domain/ports/vision_ai_service_port.py`

## Requirements

- All dead code removed; no references remain.
- `GPTResponseParser` renamed to `VisionResponseParser`; ALL imports updated including `base_dependencies.py` and `prompt_eval_loop.py`.
- `prompts/__init__.py` re-export deleted; all importers reference `domain.services.prompts.system_prompts` directly.
- Port docstring no longer says "OpenAI Vision API".
- `pytest` green before and after (test cleanup precedes file deletion).

## Implementation Steps

> **Critical order**: steps 1–3 (event_bus.py cleanup) MUST precede steps 4–5 (file deletion) to avoid ImportError on startup.

1. **Clean up `event_bus.py` first**: remove imports at lines 43, 121 and subscribe block at lines 635-642.
2. **Remove test references**: delete or rewrite the `analyze-url` test cases in `test_food_guard_command_handlers.py` and `test_meals_api.py:89,114,123,133`. Run `pytest` — must pass before proceeding.
3. Delete `src/app/events/meal/meal_image_uploaded_event.py`.
4. Delete `src/app/handlers/event_handlers/meal_analysis_event_handler.py`.
5. Delete `src/app/commands/meal/analyze_meal_image_by_url_command.py`.
6. Delete `src/app/handlers/command_handlers/analyze_meal_image_by_url_command_handler.py`.
7. Remove `VisionAIService.analyze_by_url()` from `vision_ai_service.py`.
8. Remove `BasicAnalysisStrategy._legacy_analysis_prompt()` from `meal_analysis_strategy.py`.
9. Rename `src/domain/parsers/gpt_response_parser.py` → `vision_response_parser.py`; rename class `GPTResponseParser` → `VisionResponseParser`. Update ALL imports: `grep -r GPTResponseParser src tests` — must include `base_dependencies.py` (rename `get_gpt_parser()` to `get_vision_parser()`) and `prompt_eval_loop.py`.
10. Fix port docstring in `vision_ai_service_port.py`: replace "OpenAI Vision API" with "Vision AI provider (currently Gemini)".
11. Delete `src/infra/services/ai/prompts/__init__.py`; update any importer to import directly from `domain.services.prompts.system_prompts`.
12. Run `pytest`, `ruff check src`, `mypy src` to confirm clean.

## Related Code Files

- Delete: `src/app/events/meal/meal_image_uploaded_event.py`
- Delete: `src/app/handlers/event_handlers/meal_analysis_event_handler.py`
- Delete: `src/app/commands/meal/analyze_meal_image_by_url_command.py`
- Delete: `src/app/handlers/command_handlers/analyze_meal_image_by_url_command_handler.py`
- Delete: `src/infra/services/ai/prompts/__init__.py`
- Modify: `src/api/dependencies/event_bus.py` (imports + subscribe block)
- Modify: `src/api/base_dependencies.py` (rename `get_gpt_parser` → `get_vision_parser`, update import)
- Modify: `src/domain/services/meal_analysis/prompt_eval_loop.py` (update `GPTResponseParser` import)
- Modify: `src/infra/adapters/vision_ai_service.py` (remove `analyze_by_url`)
- Modify: `src/domain/strategies/meal_analysis_strategy.py` (remove `_legacy_analysis_prompt`)
- Rename: `src/domain/parsers/gpt_response_parser.py` → `vision_response_parser.py`
- Modify: `src/domain/ports/vision_ai_service_port.py`
- Modify/delete: `tests/unit/handlers/command_handlers/test_food_guard_command_handlers.py` (analyze-url test cases)
- Modify: `tests/integration/api/test_meals_api.py` (remove lines 89,114,123,133)

## Success Criteria

- [x] `pytest` passes at each step (after test cleanup, after file deletion, after rename).
- [x] `ruff check src tests` passes.
- [x] `mypy src` passes.
- [x] `grep -r "MealImageUploadedEvent\|MealAnalysisEventHandler\|AnalyzeMealImageByUrl\|GPTResponseParser\|get_gpt_parser\|_legacy_analysis_prompt\|analyze_by_url" src tests` returns zero hits.
- [x] Route smoke test passes: `/meals/image/analyze`, `/meals/parse-text`, `/foods/barcode/*`, `/meal-suggestions/*`, `/ingredients/recognize`.

## Risk Assessment

Low risk — pure deletion and rename. Two sequencing constraints: (1) event_bus.py imports cleaned before file deletion, (2) test files cleaned before handlers deleted. Confirm `importlinter` passes after `prompts/__init__.py` removal.
