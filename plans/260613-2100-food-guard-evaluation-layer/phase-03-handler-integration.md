---
phase: 3
title: "Handler Integration"
status: completed
priority: P1
effort: "4h"
dependencies: [2]
---

# Phase 3: Handler Integration

## Context Links

- `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- `src/app/handlers/command_handlers/analyze_meal_image_by_url_command_handler.py`
- `src/app/handlers/event_handlers/meal_analysis_event_handler.py`
- `src/api/dependencies/event_bus.py`
- `tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py`
- `tests/unit/handlers/command_handlers/test_upload_image_consistency.py`

## Overview

Use the parser guard in all registered meal image command handlers before `parse_to_nutrition`. Keep existing `has_food` validation after parsing as a fallback for malformed or overconfident AI output.

## Key Insights

- Upload flow should reject after Cloudinary upload and vision response, before DB meal creation.
- Scan-by-url flow should reject after download/compression/vision, before DB meal creation.
- Legacy image URL handler creates an `ANALYZING` meal before vision. Guarding it should mark that meal failed, or the handler should be removed in a separate dead-code cleanup if current routes no longer expose it.

## Requirements

- Functional: explicit `is_food:false` raises `ValueError("Image does not appear to contain food")` or equivalent stable non-food message.
- Functional: `parse_to_nutrition` is not called when guard is false.
- Functional: translation and cache invalidation are not called for rejected scans.
- Functional: existing `has_food` error remains for empty nutrition or zero-calorie output.
- Non-functional: do not add application-to-infra imports.

## Architecture

Shared guard pattern:

```python
vision_result = await ...
if not self.gpt_parser.parse_is_food(vision_result):
    raise ValueError("Image does not appear to contain food")
nutrition = self.gpt_parser.parse_to_nutrition(vision_result)
```

If duplicated in three handlers, keep it as two lines for KISS. Only extract a helper if duplication grows beyond these handlers.

## Related Code Files

- Modify: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Modify: `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- Modify: `src/app/handlers/command_handlers/analyze_meal_image_by_url_command_handler.py`
- Modify/Create: handler tests under `tests/unit/handlers/command_handlers/`

## Implementation Steps

1. Add upload handler unit test:
   - vision returns `structured_data.is_food=false`.
   - `parse_is_food` false.
   - `parse_to_nutrition` not called.
   - `uow.meals.save`, translation, cache invalidation not called.
2. Add scan-by-url handler unit test with same guard behavior.
3. Add legacy URL handler test or deletion decision:
   - If handler remains registered, guard false must not mark meal ready.
   - If route/command is removed by another plan before implementation, update this phase and remove the stale handler from registration.
4. Add guard immediately after vision result in each handler.
5. Leave existing `has_food` block unchanged except message consistency if needed.
6. Ensure `AIUnavailableError` and provider/runtime failures keep existing behavior; only explicit guard false maps to non-food validation.

## Todo List

- [x] Upload false guard test.
- [x] Scan-by-url false guard test.
- [x] Legacy handler guard/removal test.
- [x] Guard added before `parse_to_nutrition`.
- [x] Translation/cache invalidation skipped on guard rejection.
- [x] Latent background event handler guarded before `parse_to_nutrition`.

## Success Criteria

- [x] Focused handler tests pass.
- [x] No meal record is created in upload/scan-by-url false-guard paths.
- [x] Legacy handler cannot persist READY nutrition for explicit non-food.
- [x] Real-food handler tests continue passing.

## Risk Assessment

- Risk: orphan Cloudinary upload still exists for upload false guard. Mitigation: current flow already accepts orphan on analysis failure; do not add cleanup complexity here.
- Risk: legacy handler pre-creates failed meals. Mitigation: acceptable if command remains registered; long-term dead-code cleanup belongs to bandwidth plan.
- Risk: duplicate guard logic. Mitigation: keep inline; avoid premature abstraction.

## Security Considerations

- Do not log raw image URLs or AI response on rejection.
- ValueError details must not include provider payload.

## Next Steps

Verify API error mapping and legacy route surface.
