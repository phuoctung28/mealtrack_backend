---
title: "AI Rearchitecture and Beverage Scan"
description: "Consolidate Gemini AI layer to one service/registry/extractor, add branded-beverage vision recognition, and eliminate the meals+hydration_entries dual-write anti-pattern. Zero mobile changes, same API surface."
status: pending
priority: P1
effort: "2-3 weeks"
branch: "delivery"
tags: [ai, beverage, refactor, architecture, backend]
blockedBy: []
blocks: []
created: "2026-06-16T08:34:42.891Z"
createdBy: "ck:plan"
source: skill
---

# AI Rearchitecture and Beverage Scan

## Overview

Three coordinated goals shipped in sequence:

1. **Boring AI layer**: one `GeminiService`, one prompt registry, one JSON extractor, zero dead code, zero legacy shims.
2. **Branded beverage scanning**: extend `VISION_ANALYSIS` prompt + `VisionNutritionResponse` contract so Gemini reads brand, container volume, and nutrition panel from the label. Same `POST /v1/meals/image/analyze` endpoint, same response shape to mobile.
3. **Single source of truth for drinks**: `hydration_entries` only. Activities feed reads both `meals` and `hydration_entries`. `LogCaloricDrinkCommand` stops writing a meal row. Daily kcal totals sum both tables.

**Blocked by**: `260613-1359-llm-nutrition-output-contracts` phases 4–5 must complete first (both plans touch `vision_ai_service.py`, `gpt_response_parser.py`, and shared handlers).

## Phases

| Phase | Name | Status | Effort |
|-------|------|--------|--------|
| 1 | [Dead Code Cleanup](./phase-01-dead-code-cleanup.md) | Pending | 0.5d |
| 2 | [AI Core Consolidation](./phase-02-ai-core-consolidation.md) | Pending | 2–3d |
| 3 | [Beverage Scanning and Single-Source Persistence](./phase-03-beverage-scanning-and-single-source-persistence.md) | Pending | 3–5d |
| 4 | [Docs and Observability](./phase-04-docs-and-observability.md) | Pending | 0.5d |

## Dependencies

**blockedBy**: `plans/260613-1359-llm-nutrition-output-contracts/` — in-progress; phases 4–5 (flow integration, parser replacement) overlap the same AI adapter/parser files. Wait for that plan to reach `completed` before starting Phase 1.

**blocks**: none.

## Non-goals (explicit)

- Second AI provider (OpenAI/Claude) — Gemini-only.
- External OCR (Tesseract, Cloud Vision) — Gemini-native only.
- New API routes or response fields exposed to mobile.
- Barcode beverage path hardening (future work).
- Persistent scanned-beverage catalog table/dedupe (future work).
- `legacy_meal_id` column drop (follow-up migration after one release cycle).
- Mobile app changes.

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Phase 2 refactor breaks meal scan during cutover | Full test suite + smoke tests on each sub-PR; keep old paths until new path is verified |
| Gemini misreads volume on glossy/partial labels | Container-type heuristics as fallback; `label_source: "estimate"` flag for analytics |
| Daily kcal wrong after dual-write removal | Phase 3c MUST ship before Phase 3d; all three calorie-aggregation handlers (weekly_budget, nutrition_bulk, daily_macros) updated before dual-write removal |
| Activities timeline misses drinks during 3c→3d window | Strict ship order: 3c before 3d; feed deduplicates by `legacy_meal_id` via explicit set-filter algorithm |
| Orphan meal rows after 3d | One-shot cleanup script in Phase 3e with dry-run before execution |
| New beverage prompt section hurts food-scan accuracy | Run existing eval set before merging Phase 3a; only ship if non-beverage accuracy unchanged |

## Red Team Review

### Session — 2026-06-16

**Reviewers:** Security Adversary, Failure Mode Analyst, Assumption Destroyer
**Findings:** 15 (all 15 accepted, 0 rejected)
**Severity breakdown:** 5 Critical, 5 High, 5 Medium

| # | Finding | Severity | Disposition | Applied To |
|---|---------|----------|-------------|------------|
| F1 | Pydantic `require_foods_for_food_images` validator rejects every beverage scan (`is_food=True, foods=[]`) | Critical | Accept | Phase 3, §3a step 2 |
| F2 | `WeeklyBudgetService._sum_meals()` + `GetNutritionBulkQueryHandler._build_date_summary()` excluded from 3c scope — beverage kcal vanishes from weekly budget + calendar after 3d | Critical | Accept | Phase 3, §3c steps 4-5; Related Code Files |
| F3 | Phase 2 creates `GeminiService` but never resolves `VisionAIServicePort` — DI wiring breaks every meal scan at deploy | Critical | Accept | Phase 2, §2a adapter strategy decision |
| F4 | `AnalyzeMealImageByUrl` registered in `event_bus.py:346-354` with live tests — Phase 1 deletion breaks `pytest` | Critical | Accept | Phase 1, step 2 (test cleanup before file deletion) |
| F5 | `UserContextAwareAnalysisStrategy` live in `UploadMealImageImmediatelyHandler:78-86` and `ScanByUrlCommandHandler:96-103` — Phase 2d deletion breaks user-description scanning | Critical | Accept | Phase 2, §2d (keep + slim; do not delete) |
| F6 | Phase 3d removes `meal_id: saved.meal_id` from `LogCaloricDrinkCommand` response — mobile delete path breaks | High | Accept | Phase 3, §3d step 3 |
| F7 | Phase 3c dedup logic has no implementation path — naive append double-counts pre-3d drinks | High | Accept | Phase 3, §3c step 1 (explicit `meal_id_set` algorithm) |
| F8 | `BeverageMetadata.brand`/`product_name` no `max_length` — all other contract strings are bounded | High | Accept | Phase 3, §3a step 1; §3b step 1 (VARCHAR(100)) |
| F9 | `hydration_weight` driven by AI-returned `sugar_per_100ml` with no floor when `label_source="estimate"` | High | Accept | Phase 3, §3b step 4 (conservative default) |
| F10 | `kcal_per_100ml=None` null guard missing — `TypeError` when nutrition panel unreadable | High | Accept | Phase 3, §3b step 4 (null guard + float type) |
| F11 | Phase 1 step order causes `ImportError`: source files deleted before `event_bus.py` imports removed | Medium | Accept | Phase 1 (reordered steps; event_bus.py cleanup first) |
| F12 | `label_source="estimate"` silently stored as ground truth — no WARNING log, no confidence signal | Medium | Accept | Phase 3, §3b step 4 (WARNING log) |
| F13 | Phase 3c Step 5 "update daily nutrition aggregate" is misleading — macros handler guard already correct | Medium | Accept | Phase 3, §3c step 3 (verify guard; do not remove) |
| F14 | Phase 3b beverage branch calls `after_meal_write` — hydration cache keys not invalidated | Medium | Accept | Phase 3, §3b step 4 (`after_hydration_write`) |
| F15 | `GPTResponseParser` rename misses `base_dependencies.py:5,130,137` and `prompt_eval_loop.py:6-30` | Medium | Accept | Phase 1 (added to Related Code Files; step 9 updated) |

### Whole-Plan Consistency Sweep

All 15 findings applied inline to phase files. Cross-file checks:

- **phase-01**: Step order corrected (event_bus imports before file deletion); `base_dependencies.py` and `prompt_eval_loop.py` added to Related Code Files; test-cleanup step added; success-criterion grep updated to include `get_gpt_parser`.
- **phase-02**: Adapter strategy decision documented as mandatory pre-step; `UserContextAwareAnalysisStrategy` explicitly kept in 2d; Requirements section updated to reflect 3-strategy slim (not 2-strategy delete).
- **phase-03**: Validator bypass added to 3a; prompt spec updated (`is_food=False` for beverages); `brand`/`product_name` bounded; null guards for `kcal_per_100ml`/`sugar_per_100ml`; conservative `hydration_weight` when `label_source="estimate"`; WARNING log added; `after_hydration_write` substituted for `after_meal_write` in beverage branch; `GetWeeklyBudgetQueryHandler` and `GetNutritionBulkQueryHandler` added to 3c scope and Related Code Files; explicit `meal_id_set` dedup algorithm; 3d `meal_id` mapping explicit; 3c Step 5 rewritten to preserve `has_legacy_hydration` guard.
- **plan.md**: Risk Register updated (dual-write risk now names all three aggregation handlers; dedup row references explicit algorithm).
- **No unresolved contradictions remain.** Phase 4 (docs/observability) is unaffected by red team findings.
