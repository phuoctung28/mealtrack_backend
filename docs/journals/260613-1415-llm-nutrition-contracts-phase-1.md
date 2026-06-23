---
title: "LLM Nutrition Output Contracts Phase 1"
date: "2026-06-13 14:15"
phase: "phase-01-provider-structured-vision-spike"
component: "AI provider contract"
status: "completed"
---

## Context

Phase 1 of `plans/260613-1359-llm-nutrition-output-contracts/plan.md` was limited to the provider boundary. The goal was to spike structured vision output without changing downstream parsing, storage, or domain rules.

## What Happened

We added optional keyword-only `schema` support to the AI vision contract, forwarded it through `AIModelManager`, and taught `GeminiProvider` to use `with_structured_output(schema, include_raw=True)` for multimodal requests when a schema is present. The raw JSON path stayed intact for calls that do not provide a schema. That kept the change narrow instead of turning Phase 1 into a hidden parser rewrite.

## Decisions

- Keep the change at the provider contract only.
- Make `schema` optional and keyword-only so existing callers do not break.
- Preserve the no-schema raw JSON flow exactly as-is.
- Use structured output only for vision/multimodal calls, not for every AI path.

## Verification

- 64 related tests passed via `uv`.
- `ruff`, `mypy`, `black --check`, and `py_compile` all passed on the touched source.
- Tester subagent reported only an environment issue: project `uv` works, host Python is not suitable.
- Code reviewer found no issues.

## Next

- Phase 2 should define the canonical AI nutrition contracts.
- The current parser fallback stays isolated until later phases replace it.
- Future work should keep the provider boundary stable; expanding scope here would have been premature and noisy.

