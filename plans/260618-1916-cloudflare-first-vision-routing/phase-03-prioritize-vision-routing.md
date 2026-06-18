---
phase: 3
title: "Prioritize vision routing"
status: pending
priority: P1
effort: "4h"
dependencies: [2]
---

# Phase 3: Prioritize vision routing

## Overview

Wire CF vision into `AIModelManager` so meal and ingredient image scans try Cloudflare first, then Gemini fallbacks.

## Requirements

- Functional: CF vision model is first in `MEAL_SCAN` and `INGREDIENT_SCAN` chains when enabled.
- Functional: Gemini-only behavior remains when CF disabled, missing credentials, or missing vision model.
- Functional: text-purpose routing remains independent from vision-purpose routing.
- Non-functional: no public API shape changes and no prompt/parser contract changes.

## Architecture

Add separate vision routing instead of overloading `CLOUDFLARE_WORKERS_AI_TEXT_PURPOSES`.

Settings:

```python
CLOUDFLARE_WORKERS_AI_VISION_ENABLED: bool = True
CLOUDFLARE_WORKERS_AI_VISION_MODEL: str = "@cf/google/gemma-4-26b-a4b-it"
CLOUDFLARE_WORKERS_AI_VISION_PURPOSES: str = "meal_scan,ingredient_scan"
```

Manager changes:
- `_maybe_add_cf_provider()` passes text and vision config to provider.
- register `vision_model` in `_model_provider_overrides`.
- add `_prepend_cf_to_vision_chains(cf_model, vision_purposes_csv)`.
- keep `_append_cf_to_text_chains()` behavior unchanged.

Target chain when enabled:

```text
meal_scan:
@cf/google/gemma-4-26b-a4b-it
gemini-3.1-flash-lite
gemini-3.5-flash
gemini-2.5-flash
```

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/config/settings.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/.env.example`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/ai/ai_model_manager.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/services/ai/test_ai_model_manager.py`
- No change expected: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/vision_ai_service.py`

## Implementation Steps

1. Add settings fields and `.env.example` entries for CF vision.
2. Update `_make_cf_settings()` test helper with vision fields.
3. Update manager provider construction to pass vision config.
4. Register the vision model override only when vision model is non-empty.
5. Add/prepend CF only for valid configured `ModelPurpose` values.
6. Replace existing tests that assert vision remains Gemini-only:
   - enabled path should assert CF model first for meal and ingredient scan.
   - disabled path should assert Gemini-only.
   - failure path should assert CF vision attempted before Gemini fallback.
7. Keep barcode Gemini-only by default.

## Todo List

- [ ] Add vision env settings.
- [ ] Add vision chain prepending.
- [ ] Update old Gemini-only vision tests.
- [ ] Add CF-fails-then-Gemini vision fallback test.
- [ ] Confirm text routing tests still pass.

## Success Criteria

- [ ] `get_fallback_chain(ModelPurpose.MEAL_SCAN)[0]` is CF vision model when enabled.
- [ ] `generate_with_vision()` attempts CF first and Gemini second on CF failure.
- [ ] With CF disabled or incomplete config, existing Gemini chain is unchanged.
- [ ] Text chains keep current CF priority behavior.

## Risk Assessment

Risk: one CF model ID is used for text and vision in some tests, hiding override bugs. Mitigation: add a test where text model and vision model differ.

Risk: malformed `VISION_PURPOSES` silently changes nothing. Mitigation: ignore unknown values but log a warning with only purpose names.

## Security Considerations

Settings must not print tokens. Logs may include model ID and purpose, not prompt/image/user content.

## Next Steps

Proceed to Phase 4 after focused model-manager and provider tests pass locally.
