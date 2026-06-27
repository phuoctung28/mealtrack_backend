# Phase 04 Docs And Verification

## Context Links

- Beverage docs: `docs/beverage-scan.md`
- API docs: `docs/api-endpoints.md`
- Hydration docs: `docs/api-hydration.md`
- Roadmap: `docs/project-roadmap.md`
- External services docs: `docs/external-services.md`

## Overview

Priority: medium.
Status: completed.

Align docs with the new meal scan contract and verify behavior.

## Requirements

- Docs no longer claim meal scan routes packaged beverages to hydration.
- Hydration APIs remain documented as the explicit hydration surface.
- Verification covers prompt, parser, upload handler, and scan-by-url handler.

## Architecture

Docs should describe the product boundary clearly:

- meal scan logs nutrition meals
- hydration endpoints log hydration
- no implicit hydration side effect from meal scan

## Related Code Files

- Modify: `docs/beverage-scan.md` or replace with deprecation note.
- Modify: `docs/project-roadmap.md`
- Modify: docs that mention beverage scan behavior.

## Implementation Steps

1. Update beverage scan docs to reflect removal/deprecation from meal endpoints.
2. Update roadmap/changelog entry for behavior change.
3. Run focused test suite.
4. Run lint/import checks if imports changed.
5. Replay local image evals if API keys are available.

## Todo List

- [x] Update docs.
- [x] Run focused tests.
- [x] Run import/lint checks.
- [x] Optionally run real OpenAI replay for pastry and drink fixtures.

## Success Criteria

- `uv run pytest` focused handler/prompt/parser tests pass.
- `uv run lint-imports` passes if import graph changed.
- Real pastry image still analyzes as food.
- Caloric drink fixture creates normal meal in tests.

## Risk Assessment

- Docs may still mention hydration-only beverage rows in historical context.
  Keep historical notes clear, but current behavior must be unambiguous.

## Security Considerations

- Real image replay must not log raw image bytes, prompts, or raw AI responses.

## Next Steps

Implementation can begin after plan review.
