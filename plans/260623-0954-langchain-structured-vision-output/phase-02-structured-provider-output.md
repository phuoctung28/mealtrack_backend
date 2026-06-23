---
phase: 2
title: "Structured Provider Output"
status: pending
priority: P1
effort: "1 day"
dependencies: [1]
---

# Phase 2: Structured Provider Output

## Overview

Make provider calls schema-valid by default. Gemini vision should use LangChain/Gemini structured output before raw parsing. Cloudflare vision should be evaluated through the existing direct Workers AI REST path, not `langchain-cloudflare`, because the LangChain Cloudflare integration reports structured output support but no image input support.

## Context Links

- `src/infra/services/ai/providers/gemini_provider.py`
- `src/infra/services/ai/gemini_model_manager.py`
- `src/infra/services/ai/providers/cloudflare_workers_ai_provider.py`
- `src/infra/adapters/vision_ai_service.py`
- `src/infra/services/ai/ai_model_manager.py`
- `tests/unit/infra/services/ai/providers/test_gemini_provider.py`
- `tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py`
- `tests/unit/infra/adapters/test_vision_ai_service.py`
- LangChain `ChatGoogleGenerativeAI.with_structured_output(..., method="json_schema")`
- Cloudflare Workers AI JSON mode docs

## Key Insights

- `GeminiProvider.generate()` already has a text structured-output path when `schema` is passed.
- `GeminiProvider.generate_with_vision()` currently calls `llm.invoke(messages)` and parses raw text.
- LangChain Google GenAI docs list both structured output and image input support. Docs recommend `method="json_schema"` because it uses Gemini native structured output.
- Current code has a direct Cloudflare vision path with REST/image support. Do not undo it, but do require schema/JSON contract proof before Cloudflare is primary.
- `langchain-cloudflare` is not the right image path unless its feature matrix changes; direct REST remains the Cloudflare path for this repo.

## Requirements

- Functional: meal image scans use structured output first.
- Functional: image input format remains compatible with current LangChain message shape.
- Functional: Cloudflare vision either returns schema-valid JSON or is treated as failed/degraded and falls through according to provider policy.
- Functional: fallback chain behavior in `AIModelManager.generate_with_vision()` stays unchanged.
- Non-functional: no new provider abstraction unless unavoidable.
- Non-functional: no raw AI response logging.

## Architecture

Keep structured output and provider-specific contract handling inside providers. `VisionAIService` continues to call `AIModelManager.generate_with_vision()` and receives a dict. `AIModelManager` remains provider-agnostic, but it can classify a provider result as failed if validation fails.

Proposed provider flow:

```python
llm = get_model_for_purpose(...)
structured = llm.with_structured_output(
    VisionAnalyzeResponse.model_json_schema(),
    method="json_schema",
)
parsed = structured.invoke(messages)
return normalize_to_dict(parsed)
```

If LangChain returns `parsed=None`, raises unsupported multimodal structured output, or returns a raw `AIMessage`, fall back to current `llm.invoke()` plus parser.

Cloudflare provider flow:

1. Send direct Workers AI vision request with explicit JSON/schema instructions.
2. Use Cloudflare JSON mode only if the target model/API accepts it in real tests.
3. Validate returned JSON with `VisionAnalyzeResponse`.
4. On schema/parser failure, return a classified provider error for fallback instead of pretending success.

## Related Code Files

- Modify: `src/infra/services/ai/providers/gemini_provider.py`
- Modify: `src/infra/services/ai/providers/cloudflare_workers_ai_provider.py`
- Modify: `tests/unit/infra/services/ai/providers/test_gemini_provider.py`
- Modify: `tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py`
- Modify: `tests/unit/infra/adapters/test_vision_ai_service.py`
- Read: `src/infra/services/ai/gemini_model_manager.py`
- Read: `src/infra/services/ai/ai_model_manager.py`

## Implementation Steps

### Tests Before

1. Add provider test: `generate_with_vision()` calls `with_structured_output(..., method="json_schema")` and returns parsed dict.
2. Add provider test: Pydantic object result is converted with `model_dump()`.
3. Add provider test: dict result is returned as dict.
4. Add fallback test: structured output raises or returns no parsed value, raw content parser is used.
5. Add Cloudflare test: valid JSON/schema returns normalized dict.
6. Add Cloudflare test: non-JSON/object-literal/prose response is classified as schema or parse failure.
7. Add manager test: `ModelPurpose.MEAL_SCAN` fallback chain behavior unchanged except failed validation can advance to the next provider.

### Refactor

1. Import `VisionAnalyzeResponse` into `GeminiProvider`.
2. Extract helper to normalize LangChain structured output return shapes:
   - Pydantic model
   - dict
   - `{"parsed": ...}` when `include_raw=True`
3. Update `generate_with_vision()` to try structured output before raw parse.
4. Keep `max_tokens`, `purpose_hint`, and message construction unchanged.
5. Avoid cache changes; vision path does not currently use Gemini context cache.
6. In Cloudflare provider, validate parsed response against `VisionAnalyzeResponse` before returning.
7. Keep parser fallback shared through `ai_json_utils.extract_json()`; do not duplicate raw parser logic in providers.

### Tests After

1. Run provider tests.
2. Run vision adapter tests.
3. Run AI model manager tests for fallback chain.

## Success Criteria

- [ ] `generate_with_vision()` no longer relies on raw text parsing for the normal success path.
- [ ] Cloudflare vision cannot return malformed text as successful provider output.
- [ ] Fallback parser path is still covered by tests.
- [ ] Existing `VisionAIService` API stays unchanged.
- [ ] `uv run pytest tests/unit/infra/services/ai/providers/test_gemini_provider.py tests/unit/infra/adapters/test_vision_ai_service.py tests/unit/infra/services/ai/test_ai_model_manager.py -q` passes.

## Risk Assessment

Risk: LangChain structured output may not work with image messages for a specific installed version even if docs list both features. Mitigation: implement fallback and test both structured success and structured failure.

Risk: `SystemMessage` handling with multimodal Gemini can be provider-sensitive. Current manager sets `convert_system_message_to_human=True`; keep current message structure unless tests prove it fails.

Risk: Cloudflare JSON mode support may differ by model. Mitigation: make JSON mode/model support a live dry-run gate and keep prompt-only JSON plus validation as fallback.

## Security Considerations

No raw base64 images, image URLs, provider payloads, or prompt bodies in logs. Structured-output failures should log only provider, model, purpose, stage, and exception class.
