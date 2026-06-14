---
phase: 1
title: "Research and Contract"
status: completed
priority: P1
effort: "2h"
dependencies: []
---

# Phase 1: Research and Contract

## Context Links

- `plans/reports/brainstorm-260613-1738-food-guard-evaluation-layer-report.md`
- `plans/260613-2100-food-guard-evaluation-layer/research/researcher-01-code-path-contract-report.md`
- `plans/260613-2100-food-guard-evaluation-layer/research/researcher-02-cost-failure-test-report.md`
- `src/domain/services/prompts/system_prompts.py`
- `src/domain/parsers/gpt_response_parser.py`
- `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- `src/app/handlers/command_handlers/analyze_meal_image_by_url_command_handler.py`

## Overview

Lock the exact product and technical contract before code. This phase corrects the brainstorm report's overclaims and defines edge behavior so implementation is not prompt-only guesswork.

## Key Insights

- Single-stage guard is post-vision, not pre-Gemini.
- The value is safer refusal and less parser/persistence work, not image-input cost elimination.
- Three registered command handlers need a decision; two are live routes, one is legacy-but-registered.
- Rejected scans do not persist a meal, so observability must be log/metric based.

## Requirements

- Functional: define accepted, rejected, and ambiguous image classes.
- Functional: document `is_food` semantics: missing field defaults safe-open, explicit false rejects.
- Non-functional: no new DB, cache, model purpose, local image ML, or heavy dependency.
- Non-functional: no raw image URL, raw AI response, or food payload logging.

## Architecture

The contract stays in the domain parser/prompt layer. Application handlers consume a domain parser method and keep the existing `has_food` check as fallback.

```
VisionAIService -> structured_data.is_food -> GPTResponseParser.parse_is_food
    false -> ValueError -> API NOT_FOOD_IMAGE
    true/missing -> parse_to_nutrition -> existing has_food fallback
```

## Related Code Files

- Modify: `src/domain/services/prompts/system_prompts.py`
- Modify: `src/domain/parsers/vision_response_models.py`
- Modify: `src/domain/parsers/gpt_response_parser.py`
- Modify: image command handlers in `src/app/handlers/command_handlers/`
- Modify/Create tests under `tests/unit/domain/`, `tests/unit/handlers/`, `tests/unit/api/`

## Implementation Steps

1. Update the brainstorm report or implementation notes to replace "early rejection" with "post-vision, pre-nutrition rejection".
2. Define edge taxonomy in code-facing docs/tests:
   - Accept: clear meals, snacks, caloric drinks, raw ingredients, packaged edible products.
   - Reject: laptop, shoe, pet, empty scene, empty plate, kitchen tools, face/body photos.
   - Ambiguous: supplements, medicine-like consumables, unclear labels/menu screenshots.
3. Confirm `AnalyzeMealImageByUrlHandler` status before editing. If still registered, include guard there. If removed by another plan, delete it from this plan's touch list.
4. Confirm no route or mobile response-shape change is required for successful scans.
5. Record cost assumption: `MEAL_SCAN` starts with Flash-Lite but can fallback to Flash.

## Todo List

- [x] Contract wording avoids pre-Gemini cost-saving claim.
- [x] Edge taxonomy agreed in plan/tests.
- [x] Legacy handler inclusion confirmed against current code.
- [x] Scope remains single-stage, no new dependencies.

## Success Criteria

- [x] A developer can implement without asking what `is_food=false` means.
- [x] The plan names all handlers that must be guarded or explicitly removed.
- [x] Cost and observability claims are accurate.

## Risk Assessment

- Risk: Taxonomy too strict blocks valid food. Mitigation: safe-open missing field and keep `has_food` fallback.
- Risk: Taxonomy too loose permits hallucinated junk. Mitigation: explicit prompt branch plus handler guard before persistence.
- Risk: Simultaneous work in bandwidth plan changes `scan-by-url`. Mitigation: rebase/check files before implementation.

## Security Considerations

- Do not log raw AI response or image URL for rejected scans.
- Keep existing route auth/rate-limit behavior unchanged.

## Next Steps

Proceed to parser and prompt contract tests.
