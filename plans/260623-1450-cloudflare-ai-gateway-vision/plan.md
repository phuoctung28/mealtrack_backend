---
title: "Cloudflare AI Gateway for Vision Calls"
description: "Route both Workers AI and Gemini vision requests through Cloudflare AI Gateway for unified analytics, cost tracking, and rate limiting — while preserving existing fallback chains and privacy rules."
status: pending
priority: P1
effort: "1d"
branch: "delivery"
tags: [backend, ai, cloudflare, vision, observability, infra]
blockedBy: []
blocks: []
created: "2026-06-23T08:00:17.123Z"
createdBy: "ck:plan"
source: skill
---

# Cloudflare AI Gateway for Vision Calls

## Overview

Current AI Gateway coverage gap:

| Call path | Through CF AI Gateway? |
|-----------|----------------------|
| Workers AI **text** (LangChain) | ✅ via `ai_gateway` param |
| Workers AI **vision** (httpx REST) | ❌ bypasses gateway |
| Gemini **vision** (LangChain) | ❌ bypasses gateway |
| Gemini **text with `cached_content`** | must stay direct — out of scope |

This plan closes the vision gap for both providers. Gemini text calls with `cached_content` are excluded — context cache names are Google-side objects that break when proxied through CF AI Gateway.

### Key research decisions

- **Workers AI vision**: Pattern B — add `cf-aig-gateway-id` header to existing `_post_workers_ai()` httpx call. Zero URL changes, same auth token, minimal diff.
- **Gemini vision**: Use `google-genai` SDK (`genai.Client` with `HttpOptions(base_url=...)`) — NOT LangChain; `ChatGoogleGenerativeAI.api_endpoint` only replaces the hostname, not the full URL path (open issue, unfixed).
- **Caching**: `cf-aig-skip-cache: true` on all vision calls. Each image is unique → ~0% cache hit rate.
- **Privacy**: `cf-aig-collect-log-payload: false` on all vision gateway calls. No food image data, prompts, or responses stored in CF logs.
- **`gemini-3.1-flash-lite`** in the existing MEAL_SCAN fallback chain is a potentially invalid Google model ID — verify during Phase 2 testing.

### New setting needed

`CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED: bool` — gates Gemini vision routing independently. Defaults `false` so Workers AI gateway (Phase 1) can be deployed first.

## Phases

| Phase | Name | Status | Effort |
|-------|------|--------|--------|
| 1 | [Workers AI Vision Gateway](./phase-01-workers-ai-vision-gateway.md) | Complete | 2h |
| 2 | [Gemini Vision Gateway](./phase-02-gemini-vision-gateway.md) | Complete | 4h |
| 3 | [Observability and Validation](./phase-03-observability-and-validation.md) | Complete | 2h |

## Prerequisites (must be confirmed before Phase 1)

Verify model IDs in `src/infra/services/ai/ai_model_manager.py:38-45`. The `MEAL_SCAN` and `INGREDIENT_SCAN` chains currently contain `gemini-3.1-flash-lite` and `gemini-3.5-flash` — both are potentially invalid Google AI Studio model IDs. The sister `GeminiService` path uses the correct `gemini-2.5-flash-lite`/`gemini-2.5-flash` in `src/infra/ai/model_config.py:23-24`. If these model IDs are invalid, gateway calls will double-fail (gateway attempt + LangChain fallback for the same invalid model), consuming two full request timeouts before the chain advances to a valid model. Fix `ai_model_manager.py` FALLBACK_CHAINS before any gateway code ships.

## Dependencies

- `CLOUDFLARE_AI_GATEWAY_ID` already in `Settings` and `AIModelManager` — used by Workers AI text path
- `google-genai==2.8.0` already installed (`GeminiCacheManager` uses `genai.Client`)
- No new PyPI dependencies required
- `CLOUDFLARE_AI_GATEWAY_ID` must be set in env for gateway routing to activate
- `CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED=true` + `CLOUDFLARE_AI_GATEWAY_ID` required for Gemini path

## Architecture Risk: Dual AI Stacks

Two parallel AI services exist in the codebase:
- **`AIModelManager`** (`src/infra/services/ai/ai_model_manager.py`) — used by `VisionAIService` (confirmed live production vision path via `base_dependencies.py:109`)
- **`GeminiService`** (`src/infra/ai/gemini_service.py`) — standalone service with its own `.vision()` method and `FALLBACK_CHAINS` from `src/infra/ai/model_config.py`

This plan targets **`AIModelManager` + `GeminiProvider`** — the confirmed live path. `GeminiService` is NOT used by `VisionAIService` for vision calls but has its own vision capability. If a future consolidation switches `VisionAIService` to `GeminiService`, the gateway changes in Phase 2 become dead code. That consolidation is a separate plan scope.

Note: `tests/unit/infra/services/ai/test_ai_model_manager.py` (misleadingly named) actually tests `GeminiService`, not `AIModelManager`. New tests for `AIModelManager` gateway behavior are written in Phase 3.

## Red Team Review

### Session — 2026-06-23
**Findings:** 10 (9 accepted, 1 rejected)
**Severity breakdown:** 2 Critical, 5 High, 2 Medium accepted; 1 Medium rejected

| # | Finding | Severity | Disposition | Applied To |
|---|---------|----------|-------------|------------|
| 1 | `self._gateway_id` never stored — plan claim was false | Critical | Accept | Phase 1 Step 1 |
| 2 | Dual AI stacks — `GeminiService` parallel path not acknowledged | Critical | Accept (modified) | plan.md risk note |
| 3 | Invalid model IDs in `AIModelManager.FALLBACK_CHAINS` deferred too late | High | Accept | plan.md Prerequisites |
| 4 | Bare `except Exception` in gateway fallback too silent | High | Accept | Phase 2 Step 4 |
| 5 | `VisionAIService` hardcodes `MEAL_SCAN` for ingredient calls | High | Accept (limitation note) | Phase 3 smoke test |
| 6 | `asyncio.to_thread` wrapping `genai.Client` — use `.aio.*` async API | High | Accept | Phase 2 Step 3 |
| 7 | Phase 3 httpx mock `__aenter__` not `AsyncMock` — test would fail | High | Accept | Phase 3 Step 2 |
| 8 | `importlib.reload` in Gemini tests pollutes singleton state | High | Accept | Phase 3 Step 3 |
| 9 | `purpose_hint` forwarding steps misleading — already present | Medium | Accept | Phase 1 Step 5, Phase 3 Step 1 |
| 10 | MIME `image/jpeg` hardcoded — undocumented contract | Medium | Reject | `_compress_image` invariant is enforced |

### Whole-Plan Consistency Sweep

All accepted findings applied and cross-checked across plan.md and all phase files:
- Phase 1 Step 1: reworded — `self._gateway_id` is a NEW assignment, not additive
- Phase 1 Step 5: reworded — confirmed already present, no implementation action
- Phase 2 Step 3: `asyncio.to_thread` replaced with `await client.aio.models.generate_content()`
- Phase 2 Step 4: `except Exception` now `except Exception as exc: logger.warning(...)` + metric
- Phase 3 Step 1: reworded — confirmed already present, read-only check
- Phase 3 Step 2: httpx mock fully rewritten with `AsyncMock` for `__aenter__`/`__aexit__`
- Phase 3 Step 3: `importlib.reload` replaced with direct instantiation pattern
- Phase 3 smoke test: ingredient scan metadata documented as known limitation
- plan.md: Prerequisites section added (model ID verification before Phase 1)
- plan.md: Architecture Risk section added (dual AI stacks, misnamed test file)

No remaining contradictions found across phases.

## Acceptance Criteria

- Workers AI vision calls include `cf-aig-gateway-id` header when `CLOUDFLARE_AI_GATEWAY_ID` is set
- Gemini vision calls route through CF AI Gateway `google-ai-studio` endpoint when both settings are set
- No food image bytes, prompts, or responses stored in CF logs (`cf-aig-collect-log-payload: false`)
- Cache bypassed on all vision calls (`cf-aig-skip-cache: true`)
- All existing tests pass; fallback chain and circuit breaker behavior unchanged
- Gemini text calls with `cached_content` remain on direct-to-Google LangChain path
