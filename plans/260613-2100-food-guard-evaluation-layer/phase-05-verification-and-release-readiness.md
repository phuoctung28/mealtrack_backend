---
phase: 5
title: "Verification and Release Readiness"
status: completed
priority: P2
effort: "2h"
dependencies: [4]
---

# Phase 5: Verification and Release Readiness

## Context Links

- `docs/testing-standards.md`
- `docs/code-standards.md`
- `docs/api-endpoints.md`
- `docs/project-roadmap.md`
- `.importlinter`
- `pyproject.toml`

## Overview

Verify the guard without full-system churn. Update docs only if public API behavior or implementation guidance changed.

## Key Insights

- This is no-DB, no-cache, no-infra work.
- The highest risk is misclassification and parser coercion, not SQL or deployment.
- The repo's pre-push hook can surface unrelated test-isolation issues; focused gates should run first.

## Requirements

- Functional: focused unit/API tests pass.
- Functional: real-food behavior unchanged.
- Non-functional: ruff/black/mypy/import-linter gates considered before merge.
- Non-functional: docs/changelog updated only if there is a meaningful external behavior note.

## Architecture

Verification sequence:

```
domain parser/prompt tests
-> handler tests
-> API route tests
-> architecture/import guard
-> optional broader unit suite
```

## Related Code Files

- Modify if needed: `docs/api-endpoints.md`
- Modify if needed: `docs/project-roadmap.md`
- Modify if needed: `docs/project-changelog.md` if present
- No migration files expected.

## Implementation Steps

1. Run focused tests:
   - `pytest tests/unit/domain/parsers/test_gpt_response_parser.py tests/unit/domain/parsers/test_vision_response_models.py tests/unit/domain/services/prompts/test_prompt_constants.py -q`
   - `pytest tests/unit/handlers/command_handlers -q`
   - `pytest tests/unit/api/test_app_smoke_routes.py tests/unit/api/test_small_v1_routers.py -q`
2. Run architecture checks relevant to layer boundaries:
   - `lint-imports` if available.
   - `ruff check src tests`.
3. Run broader safe suite if time:
   - `pytest tests/unit -q`
4. Confirm no generated migration.
5. Confirm `git diff --check`.
6. Update docs/changelog only if implementation changes public documented behavior.
7. Prepare release note:
   - "Meal image scans now reject explicit non-food images before nutrition parsing."
   - "No success response-shape change."

## Todo List

- [x] Focused parser/prompt tests pass.
- [x] Focused handler/API tests pass.
- [x] Layer/import checks pass or blockers documented.
- [x] No migration generated.
- [x] Docs impact classified.
- [x] Release note written.

## Success Criteria

- [x] Explicit non-food images do not create READY meals.
- [x] Real food scans still create READY meals with macro-derived calories.
- [x] Provider outage behavior unchanged.
- [x] No raw AI/image data logged in new code.
- [x] Implementation branch ready for PR/review.

## Verification Results

- `uv run --python 3.11 black --check` on touched files passed.
- `uv run --python 3.11 ruff check` on touched files passed.
- `uv run --python 3.11 pytest tests/unit/domain/parsers/test_gpt_response_parser.py tests/unit/domain/parsers/test_vision_response_models.py tests/unit/domain/services/prompts/test_prompt_constants.py tests/unit/domain/model/ai/test_nutrition_contracts.py tests/unit/infra/adapters/test_vision_ai_service_resilience.py tests/unit/handlers/command_handlers/test_upload_image_consistency.py tests/unit/handlers/command_handlers/test_food_guard_command_handlers.py tests/unit/api/test_app_smoke_routes.py -q` passed: 91 tests.

Docs impact: minor. Public success response shape is unchanged; release note: meal image scans now reject explicit non-food images after vision and before nutrition parsing.

## Risk Assessment

- Risk: broad unit suite exposes unrelated failures. Mitigation: report separately; do not hide food-guard failures.
- Risk: docs overpromise "early" rejection. Mitigation: release wording says before nutrition parsing, not before Gemini.
- Risk: tests use mocks that hide parser issues. Mitigation: include parser-level tests with raw structured payloads.

## Security Considerations

- Confirm no new secret/env variable.
- Confirm no raw payload logging.
- Confirm route auth unchanged.

## Next Steps

After user approval, execute with `/ck:cook /Users/alexnguyen/Desktop/Nut/mealtrack_backend/plans/260613-2100-food-guard-evaluation-layer/plan.md`.
