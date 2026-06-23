---
phase: 4
title: "Docs and Observability"
status: pending
priority: P2
effort: "0.5d"
dependencies: [3]
---

# Phase 4: Docs and Observability

## Overview

Refresh affected docs, write a new beverage-scan developer guide, and add structured logging to `GeminiService` for A/B + accuracy dashboards. Ships as a single PR after Phase 3 is complete.

## Context Links

- External services doc: `docs/external-services.md`
- System architecture doc: `docs/system-architecture.md`
- New doc to create: `docs/beverage-scan.md`
- GeminiService: `src/infra/ai/gemini_service.py`

## Implementation Steps

1. **Update `docs/external-services.md`**:
   - Replace multi-provider description with single `GeminiService`.
   - Update model names: `gemini-2.5-flash-lite` (primary), `gemini-2.5-flash` (fallback).
   - Remove references to removed managers/providers.
   - Add `AIPurpose.MEAL_SCAN` beverage extension note.

2. **Update `docs/system-architecture.md`**:
   - Delete the async event flow diagram (dead path removed in Phase 1).
   - Add beverage scan flow: `POST /v1/meals/image/analyze → GeminiService → beverage branch → hydration_entries`.
   - Update AI layer diagram to show single `GeminiService`.
   - Update activities feed description to reflect dual-table read.

3. **Write `docs/beverage-scan.md`** (new file):
   - End-to-end flow: image upload → `GeminiService.vision(MEAL_SCAN)` → `BeverageMetadata` → `HydrationWriteService` → synthesized meal response.
   - Prompt versioning: how `PROMPT_VERSION` is set, how to bump it.
   - Brand defaults table: Coca-Cola, Aquarius, Pocari Sweat, Red Bull defaults.
   - How to add a new branded beverage to the eval set.
   - Volume inference heuristics (can=330ml, slim can=250ml, small PET=500ml, large PET=1500ml).
   - `hydration_weight` assignment rules (sweetened=0.7, sports=0.85, water=1.0).

4. **Add structured logging to `GeminiService`** (`src/infra/ai/gemini_service.py`):
   - Log per AI call: `{purpose, model, prompt_version, latency_ms, retry_count, fallback_used, is_beverage_scan}`.
   - Use the project's observability connector (Sentry logs / structured log format from `260613-1319-production-logging-severity-privacy-cleanup`).
   - No PII in logs (no image bytes, no user_id in the AI log line — only purpose + timing + model metadata).

## Related Code Files

- Modify: `docs/external-services.md`
- Modify: `docs/system-architecture.md`
- Create: `docs/beverage-scan.md`
- Modify: `src/infra/ai/gemini_service.py`

## Success Criteria

- [ ] `docs/external-services.md` no longer references `AIModelManager`, `GeminiModelManager`, or any removed provider.
- [ ] `docs/system-architecture.md` async event flow diagram removed; beverage scan flow added.
- [ ] `docs/beverage-scan.md` exists and covers end-to-end flow, prompt versioning, brand defaults, and eval setup.
- [ ] `GeminiService` logs `{purpose, model, prompt_version, latency_ms, retry_count, fallback_used}` per call.
- [ ] No PII in AI log lines (grep for user_id/email/image_url in AI log statements).

## Risk Assessment

Low risk — docs and logging only. Logging change: ensure no secrets leak into log lines (image bytes, Firebase tokens). Verified by grep on new log statements.
