---
title: "LLM Nutrition Output Contracts"
description: "Replace parser-side AI cleanup with structured nutrition contracts, bounded validation retry, deterministic mapping, and observability across image, text, and recipe AI flows."
status: in-progress
priority: P1
branch: ""
tags: [ai, nutrition, structured-output, validation, ux]
blockedBy: []
blocks: []
created: "2026-06-13T06:59:38.595Z"
createdBy: "ck:plan"
source: skill
---

# LLM Nutrition Output Contracts

## Overview

Build a contract-first boundary for MealTrack nutrition AI. Gemini returned
`quantity=150000`; the temporary parser filter prevents a crash but can silently
save incomplete nutrition. The final design makes invalid model output visible,
retryable once, then either maps deterministic validated data into domain models
or returns controlled guidance to the user.

Source report: `plans/reports/260613-1350-llm-nutrition-contract-brainstorm.md`

## Decisions

- `quantity=150000` is invalid AI output, not a food item.
- Preserve UX with one automatic retry before user-facing fallback.
- Scope image scan, text parse, and recipe AI output contracts.
- Backend derives calories from macros; AI calories are ignored metadata only.
- Keep domain invariants as the last guard, not the primary LLM validator.
- No DB schema change, mobile change, nutrition database redesign, or provider migration.

## Phases

| Phase | Name | Status | Effort |
|-------|------|--------|--------|
| 1 | [Provider Structured Vision Spike](./phase-01-provider-structured-vision-spike.md) | Completed | 0.5d |
| 2 | [Canonical AI Nutrition Contracts](./phase-02-canonical-ai-nutrition-contracts.md) | Completed | 0.5-1d |
| 3 | [Validation Retry Orchestration](./phase-03-validation-retry-orchestration.md) | Completed | 1d |
| 4 | [Flow Integration And Parser Replacement](./phase-04-flow-integration-and-parser-replacement.md) | Pending | 1-2d |
| 5 | [Evaluation Observability And Documentation](./phase-05-evaluation-observability-and-documentation.md) | Pending | 0.5d |

## Dependencies

Related plan: `plans/260612-1046-service-initiated-bandwidth-reduction/plan.md`.
Both plans may touch `gemini_provider.py`, `ai_model_manager.py`, and
`vision_ai_service.py`. No hard block: execute this plan's Phase 1 before any
optional URL-Gemini provider changes, or merge provider signature changes in one
patch.

## Validation Gate

- `uv run pytest tests/unit/infra/services/ai tests/unit/infra/adapters tests/unit/domain/parsers tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py -q`
- `uv run ruff check src tests`
- `uv run mypy src`
- `uv run python -m py_compile $(find src -name '*.py')`

## Unresolved Questions

None.
