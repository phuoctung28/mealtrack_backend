---
date: 2026-06-13 17:49
status: resolved
component: llm-nutrition-output-contracts
phase: 3
---

# Phase 3 LLM Nutrition Output Contracts

## Context

Phase 3 closed the gap between flaky LLM output and the meal analysis contract. The work centered on validation/retry orchestration for vision and text nutrition flows, with one controlled retry for invalid structured output and no retry for provider outages.

## What Happened

We treated invalid AI output as a contract failure, not parser cleanup. That changed the behavior from "best effort parsing" to "validate, repair once, then fail cleanly." Ingredient recognition stayed on its existing unstructured contract and was not forced into the nutrition schema. FatSecret divergence checks also stopped trusting AI-reported calories and now compare against backend-derived macro calories.

## Decisions

Retry exactly once for invalid structured output. Keep provider outages separate so fallback behavior stays intact. Keep ingredient recognition outside the nutrition contract because it is a different payload shape and mixing it in would have been a sloppy regression. Preserve the existing DTO shape for text parsing after validation so the API surface does not drift.

## Validation

The focused regression slice passed at 21 tests. The expanded Phase 1-3 AI boundary suite passed at 155 tests. Touched-file `ruff check`, `mypy`, `black --check`, and `py_compile` all passed. That is the part that mattered: the contract changes held under the boundary tests instead of just looking right in code review.

## Next

Phase 3 is done. Move to Phase 4 and keep the same rule: if the model violates the output contract, fail the contract first and only repair it once.
