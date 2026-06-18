---
title: "Cloudflare-first vision provider routing"
description: "Make Cloudflare Workers AI the first attempted provider for meal and ingredient image analysis, with Gemini fallback preserved."
status: complete
priority: P1
effort: "1.5d"
branch: "main"
tags: [backend, ai, infra, cloudflare, vision]
blockedBy: []
blocks: []
created: "2026-06-18T12:17:01.601Z"
createdBy: "ck:plan"
source: skill
---

# Cloudflare-first vision provider routing

## Overview

Prioritize Cloudflare Workers AI for vision image analysis in MealTrack while keeping Gemini as fallback. This addresses Gemini 504 `DEADLINE_EXCEEDED` failures on `meal_scan` without changing public scan endpoints, parser contracts, or mobile response shapes.

Current state:
- `CloudflareWorkersAIProvider` is text-only and raises `NotImplementedError` for `generate_with_vision`.
- `AIModelManager.generate_with_vision()` already skips providers without `AICapability.VISION`.
- Existing tests intentionally assert `MEAL_SCAN` and `INGREDIENT_SCAN` stay Gemini-only; implementation must update those tests deliberately.

Recommended design:
- Add explicit CF vision config: `CLOUDFLARE_WORKERS_AI_VISION_ENABLED`, `CLOUDFLARE_WORKERS_AI_VISION_MODEL`, `CLOUDFLARE_WORKERS_AI_VISION_PURPOSES`.
- Use `@cf/google/gemma-4-26b-a4b-it` as first CF vision candidate because Cloudflare marks it `Vision Yes` and its schema supports `messages[].content[].image_url`.
- Implement CF vision through Workers AI REST `ai/run` with `httpx.AsyncClient`, not the current LangChain text adapter.
- Prepend the CF vision model to `meal_scan` and `ingredient_scan` chains only when enabled and credentials/model are present.
- Preserve existing Gemini 3 chain as fallback: `gemini-3.1-flash-lite`, `gemini-3.5-flash`, `gemini-2.5-flash`.

Out of scope:
- Prompt redesign, parser rewrite, nutrition schema changes, DB migrations, mobile changes.
- Cloudflare image generation config (`CF_IMAGE_MODEL`) unrelated to image understanding.
- Making barcode use CF vision unless explicitly requested later.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Research request contract](./phase-01-research-request-contract.md) | Complete |
| 2 | [Implement provider vision](./phase-02-implement-provider-vision.md) | Complete |
| 3 | [Prioritize vision routing](./phase-03-prioritize-vision-routing.md) | Complete |
| 4 | [Verify rollout docs](./phase-04-verify-rollout-docs.md) | Complete |

## Dependencies

- No blocking unfinished plan found. `plans/260608-2251-ai-api-reliability-hardening` is completed and explicitly excluded new provider integrations.
- Requires Cloudflare account ID/API token with Workers AI permission in production.
- External docs to validate during implementation:
  - https://developers.cloudflare.com/workers-ai/models/gemma-4-26b-a4b-it/
  - https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/

## Acceptance Criteria

- CF vision is attempted first for `ModelPurpose.MEAL_SCAN` and `ModelPurpose.INGREDIENT_SCAN` when enabled.
- Gemini vision fallback still runs when CF vision returns 429, 5xx, timeout, malformed JSON, or empty content.
- CF text routing remains unchanged for configured text purposes.
- Public image upload and scan-by-url response shapes stay unchanged.
- Logs contain model/provider/error metadata only, never raw images, base64, prompts, food payloads, URLs, or raw AI responses.
- Focused unit tests, provider tests, compile check, and docs updates pass.

## Implementation Handoff

Use:
`/ck:cook /Users/alexnguyen/Desktop/Nut/mealtrack_backend/plans/260618-1916-cloudflare-first-vision-routing/plan.md`
