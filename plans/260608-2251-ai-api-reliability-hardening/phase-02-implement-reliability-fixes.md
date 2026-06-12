---
phase: 2
title: Implement reliability fixes
status: completed
priority: P1
effort: 3h
dependencies:
  - 1
---

# Phase 2: Implement reliability fixes

## Overview

Apply focused fixes to AI fallback/cache behavior, vision error semantics, ingredient payload validation, image-url analysis, and the Postgres route-test harness.

## Requirements

- Functional: provider fallback, image analysis, ingredient recognition, image-url analysis, and route tests behave correctly under the reviewed failure modes.
- Non-functional: no public success response-shape changes; no unrelated refactors.

## Architecture

Keep API routes thin. Put provider/cache compatibility in `AIModelManager` and `GeminiCacheManager`. Put URL image byte fetching and typed exception preservation in `VisionAIService`. Put request body limits in Pydantic schemas and strict decode in command handler.

## Related Code Files

- Modify: `src/infra/services/ai/gemini_cache_manager.py`
- Modify: `src/infra/services/ai/ai_model_manager.py`
- Modify: `src/infra/adapters/vision_ai_service.py`
- Modify: `src/api/schemas/request/ingredient_recognition_requests.py`
- Modify: `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py`
- Modify: `tests/conftest.py`
- Modify/Add tests under `tests/unit/infra/services/ai`, `tests/unit/infra/adapters`, `tests/unit/handlers/command_handlers`, and `tests/integration/routes`.

## Implementation Steps

1. Add cache metadata helpers that store and read cache names with model information while tolerating legacy string cache values.
2. Update `AIModelManager.generate()` to pass cache only when the cache metadata model matches the current fallback model.
3. Preserve `AIUnavailableError` through `VisionAIService.analyze_with_strategy()`.
4. Implement safe image URL fetching before calling `generate_with_vision()`: HTTP(S), status, content type, and size checks.
5. Add `IngredientRecognitionRequest.image_data` max length and strict base64 decode.
6. Replace PostgreSQL-invalid `CREATE DATABASE IF NOT EXISTS` test setup with a PostgreSQL-compatible existence check/create.
7. Add regression tests for each changed behavior.

## Success Criteria

- [ ] Fallback cache mismatch is covered by a unit test.
- [ ] Vision outage mapping is covered by route or route-adjacent test.
- [ ] URL image analysis passes actual response bytes to the vision model manager.
- [ ] Ingredient oversized and invalid base64 payloads are rejected.
- [ ] Test database setup no longer fails on PostgreSQL syntax.

## Risk Assessment

Cache metadata change has deployment risk if Redis contains legacy values. Read legacy values as cache-name-only and omit cache when the model cannot be verified.
