---
phase: 1
title: "Provider Structured Vision Spike"
status: completed
effort: "0.5d"
---

# Phase 1: Provider Structured Vision Spike

## Context Links

- Brainstorm: `plans/reports/260613-1350-llm-nutrition-contract-brainstorm.md`
- Provider text structured path: `src/infra/services/ai/providers/gemini_provider.py`
- Provider port: `src/domain/ports/ai_provider_port.py`
- Manager fallback path: `src/infra/services/ai/ai_model_manager.py`
- Vision adapter: `src/infra/adapters/vision_ai_service.py`
- Tests: `tests/unit/infra/services/ai/providers/test_gemini_provider.py`
- Tests: `tests/unit/infra/services/ai/test_ai_model_manager.py`

## Overview

Prove and implement schema plumbing for multimodal vision calls before changing
the domain parser. Text generation already supports `schema` through
`with_structured_output`; vision currently invokes Gemini and extracts raw JSON.
This phase makes `generate_with_vision(..., schema=...)` real while preserving
the existing raw JSON path when no schema is passed.

Priority: P1.

## Requirements

- Add optional `schema: type | None` to `AIProviderPort.generate_with_vision`.
- Pass `schema` through `AIModelManager.generate_with_vision`.
- In `GeminiProvider.generate_with_vision`, when schema exists:
  - Build the same multimodal message payload used today.
  - Call `llm.with_structured_output(schema, include_raw=True)`.
  - Return `parsed.model_dump()` for Pydantic models, or `dict(parsed)`.
  - Raise a controlled error if parsed output is `None`.
- Keep the current no-schema path and `_extract_json` behavior unchanged.
- Preserve circuit breaker success/failure behavior and model fallback.
- Unit tests only; do not require live Gemini credentials.

## Architecture

Provider interface stays provider-agnostic. The structured-output capability is
already represented by `AICapability.STRUCTURED_OUTPUT`; this phase extends the
vision method to use that same capability instead of adding a new service layer.

Data flow:

```text
VisionAIService
  -> AIModelManager.generate_with_vision(schema=...)
  -> GeminiProvider.generate_with_vision(schema=...)
  -> ChatGoogleGenerativeAI.with_structured_output(...)
  -> validated dict
```

## Related Code Files

Modify:

- `src/domain/ports/ai_provider_port.py`
- `src/infra/services/ai/ai_model_manager.py`
- `src/infra/services/ai/providers/gemini_provider.py`
- `tests/unit/domain/ports/test_ai_provider_port.py`
- `tests/unit/infra/services/ai/test_ai_model_manager.py`
- `tests/unit/infra/services/ai/providers/test_gemini_provider.py`

## Implementation Steps

1. Write failing provider-port/unit tests proving `generate_with_vision` accepts
   and forwards a `schema` argument.
2. Add manager test: `AIModelManager.generate_with_vision(..., schema=DummyModel)`
   passes schema to the selected provider and still records success.
3. Add Gemini provider test using a fake LLM where `with_structured_output` is
   called with the schema and receives the multimodal messages.
4. Add Gemini provider regression test for the no-schema raw JSON path.
5. Implement the port, manager, and provider signature changes.
6. Make structured vision return a plain dict from parsed Pydantic output.
7. Keep exception handling generic enough for circuit breaker fallback, but do
   not swallow schema/validation failures in this phase.
8. Run the focused tests.

## Success Criteria

- [x] `generate_with_vision(..., schema=...)` is available on the domain port.
- [x] AI model manager forwards the schema to the active provider.
- [x] Gemini provider uses structured output for multimodal messages when schema exists.
- [x] Gemini provider raw JSON extraction remains unchanged when schema is omitted.
- [x] No live external AI call is needed for test coverage.
- [x] Focused tests pass.

## Completion Notes

- Implemented `schema` as a keyword-only vision argument to avoid breaking
  existing positional provider calls.
- Verified no-schema vision behavior still uses raw JSON extraction.
- Tester gate: focused provider tests passed with project venv; environment-only
  concern for non-venv Python.
- Code-review gate: no findings.

## Risk Assessment

- Risk: LangChain structured output behaves differently for multimodal messages.
  Mitigation: isolate this in provider tests first; keep no-schema fallback path
  untouched until later phases prove the new path.
- Risk: Provider signature change breaks fake providers in tests.
  Mitigation: update all local fake provider implementations in the same patch.

## Security Considerations

- Do not log image bytes, base64 payloads, or full user food descriptions.
- Structured-output errors may include field names, not raw image content.

## Next Steps

Proceed to Phase 2 only after schema plumbing is tested locally.
