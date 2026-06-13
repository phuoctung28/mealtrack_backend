---
title: "Food Guard Evaluation Layer"
description: "Add a schema-level food/not-food guard to meal image analysis without new AI calls, local ML, DB changes, or calorie-source drift."
status: completed
priority: P2
branch: "delivery"
tags: [feature, backend, ai, api]
blockedBy: []
blocks: []
created: "2026-06-13T14:01:17.322Z"
createdBy: "ck:plan"
source: skill
---

# Food Guard Evaluation Layer

## Overview

Implement single-stage `is_food` handling for meal image analysis. Gemini still receives the image once; the guard exits after vision response and before nutrition parsing/persistence when the model explicitly says no edible food is present.

Expected output: focused PR on `delivery` with parser/prompt contract, handler integration, route-level error preservation, and focused tests. No DB migration, no new service, no new model purpose, no local CV/ML dependency.

Design source: `plans/reports/brainstorm-260613-1738-food-guard-evaluation-layer-report.md`
Review source: this plan's `research/` and `reports/` folders.

## Scope Boundary

In scope:
- Add `is_food` contract to `VISION_ANALYSIS` response model and parser.
- Use the guard in all registered meal image command handlers.
- Preserve existing `has_food` validation as fallback.
- Keep backend calorie source of truth: macros-derived calories only.

Out of scope:
- Two-stage guard prompt, CLIP/MobileNet/PyTorch, client CoreML, Cloudinary tagging.
- New DB columns, cache changes, AI model purpose/fallback edits.
- Ingredient recognition flow except regression confirmation.
- Full dead-code cleanup beyond explicitly handling the legacy image URL command.

## Cross-Plan Dependencies

| Relationship | Plan | Status | Note |
|---|---|---|---|
| Related | `260612-1046-service-initiated-bandwidth-reduction` | pending | Overlaps `scan-by-url` and dead image analysis code; no hard block, but avoid simultaneous edits. |

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Research and Contract](./phase-01-research-and-contract.md) | Completed |
| 2 | [Parser and Prompt Guard](./phase-02-parser-and-prompt-guard.md) | Completed |
| 3 | [Handler Integration](./phase-03-handler-integration.md) | Completed |
| 4 | [Route and Legacy Coverage](./phase-04-route-and-legacy-coverage.md) | Completed |
| 5 | [Verification and Release Readiness](./phase-05-verification-and-release-readiness.md) | Completed |

## Dependencies

- Google Gemini pricing is a moving external dependency. Current checked price: Flash-Lite standard paid tier $0.10 input / $0.40 output per 1M tokens; Flash fallback is materially higher.
- Current `MEAL_SCAN` fallback chain is Flash-Lite then Flash.
- Existing architecture: API routes send CQRS commands; handlers use async ports/UoW; domain owns parser and prompt contracts.

## Hard-Mode Research

- `research/researcher-01-code-path-contract-report.md`
- `research/researcher-02-cost-failure-test-report.md`

## Red Team Review

- Report: `reports/from-code-reviewer-to-planner-red-team-food-guard-plan-review-report.md`
- Accepted findings: include legacy handler, strict boolean coercion, corrected "early" wording, no rejected-scan `raw_gpt_json` persistence claim, explicit edge taxonomy.
- Whole-plan consistency sweep: no unresolved contradictions.

## Validation

Completed implementation:
- Added `is_food` to the canonical Gemini `VisionNutritionResponse`, legacy `VisionAnalyzeResponse`, prompt contract, and parser helper.
- Preserved safe-open legacy behavior for missing `is_food`; explicit false values reject before nutrition parsing.
- Guarded upload, scan-by-url, legacy analyze-by-url, and latent background analysis paths.
- Preserved existing API `NOT_FOOD_IMAGE` mapping for upload and scan-by-url.
- No DB migration, new AI call, cache change, or success response-shape change.

Verification:
- `uv run --python 3.11 black --check ...` on touched files passed.
- `uv run --python 3.11 ruff check ...` on touched files passed.
- `uv run --python 3.11 pytest ... -q` focused suite passed: 91 tests.

No blocking user questions. Default taxonomy: accept clear edible food/drinks/packaged edible products; reject non-food objects and empty scenes; keep `has_food` fallback for ambiguous scans.
