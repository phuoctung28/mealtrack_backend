---
phase: 2
title: "Implement provider vision"
status: pending
priority: P1
effort: "4h"
dependencies: [1]
---

# Phase 2: Implement provider vision

## Overview

Make `CloudflareWorkersAIProvider` a real vision-capable provider while preserving the existing LangChain-backed text path.

## Requirements

- Functional: `generate_with_vision()` sends image bytes to Workers AI and returns the same parsed `dict` shape as Gemini.
- Functional: provider advertises `AICapability.VISION` only when a vision model is configured.
- Functional: text generation behavior stays unchanged.
- Non-functional: provider uses bounded timeout, propagates 429/5xx/timeout for circuit breaker behavior, and never logs raw image/prompt/response content.

## Architecture

Keep one provider class, two transport paths:
- Text path: existing `ChatCloudflareWorkersAI` via LangChain.
- Vision path: direct Workers AI REST call with `httpx.AsyncClient`.

Constructor additions:

```python
vision_model: str = ""
vision_enabled: bool = False
```

Provider behavior:
- `supported_capabilities` starts with text/structured output.
- Add `AICapability.VISION` when `vision_enabled and vision_model`.
- `get_available_models()` returns text model and vision model without duplicates.
- `generate_with_vision()` base64 encodes bytes into a data URL, posts to `/ai/run/{model}`, extracts text, then uses `extract_ai_json`.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/ai/providers/cloudflare_workers_ai_provider.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py`
- No change expected: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/ports/ai_provider_port.py`

## Implementation Steps

1. Add vision constructor fields and store `account_id`, `api_token`, `gateway_id`, timeout for REST calls.
2. Update docstring from text-only to text plus optional vision.
3. Update `supported_capabilities` and `get_available_models`.
4. Implement private helpers:
   - `_build_vision_payload(prompt, image_data, system_message, max_tokens)`
   - `_post_workers_ai(model, payload)`
   - `_extract_response_text(payload)`
5. Implement `generate_with_vision()`:
   - reject when no vision model configured.
   - use `model` argument from manager, not hardcoded model.
   - pass `max_tokens` from kwargs, defaulting to 4096 if absent.
   - parse JSON with existing `extract_ai_json`.
6. Extend `extract_error_code()` if direct REST wraps Cloudflare errors differently.
7. Add provider tests for capability, payload shape, success parse, malformed JSON, 429, 503, timeout, and empty response.

## Todo List

- [ ] Add config-aware vision capability.
- [ ] Add direct REST vision transport.
- [ ] Normalize CF response text.
- [ ] Preserve current text tests.
- [ ] Add provider vision tests.

## Success Criteria

- [ ] Provider test suite proves CF vision can be called and parsed.
- [ ] Existing text provider tests still pass.
- [ ] No raw image/base64/prompt/response appears in logs or exception messages.

## Risk Assessment

Risk: provider file exceeds target size. Mitigation: if it gets too large, extract small private helpers in the same module first; create a new helper module only if the file approaches the hard limit.

Risk: LangChain and REST behavior diverge. Mitigation: keep transports isolated and share only JSON extraction/error-code behavior.

## Security Considerations

Use `Authorization: Bearer ...` only in request headers. Do not include token, base64 image, prompt text, or response preview in logs.

## Next Steps

Proceed to Phase 3 after provider unit tests define the new contract.
