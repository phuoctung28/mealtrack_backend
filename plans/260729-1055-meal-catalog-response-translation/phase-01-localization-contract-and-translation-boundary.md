---
phase: 1
title: Localization contract and translation boundary
status: completed
priority: P2
effort: 2h
dependencies: []
---

# Phase 1: Localization contract and translation boundary

## Overview

Define the response localization contract before implementation. Keep catalog/recommendation logic deterministic and English-canonical; localization belongs at the API projection boundary.

## Requirements

- Translate `name`, `cuisine`, optional `description`, and ingredient `display_name`.
- Preserve units, quantities, macros, calories, IDs, meal types, scores, ordering, and state.
- Use `get_request_language(request)`; do not parse raw headers or add a query/body override.
- Missing service, English target, provider error, and short output fall back to canonical text.

## Architecture

Reuse `DeepLTextTranslationService`; add one response-localizer seam only if the mapping logic cannot remain small. It receives the loaded plan/slot and returns new frozen catalog projections. It performs one deduplicated batch per response and never writes to catalog or recommendation storage.

## Related Code Files

- Read: `src/api/middleware/accept_language.py`, `src/domain/services/translation/deepl_text_translation_service.py`.
- Modify: `src/api/routes/v1/meal_recommendation_route_support.py`, route tests and contract tests.

## Implementation Steps

1. Characterize current English response shapes and all callers of the shared mapping helpers.
2. Document the field allowlist and fallback semantics in tests.
3. Decide async mapping/dependency injection shape for all six response-producing routes.
4. Confirm no DB schema, catalog model, ranking, persistence, or analytics changes are needed.

## Success Criteria

- [x] Contract covers summary, detail, and mutation responses.
- [x] Only user-facing text fields are candidates for translation.
- [x] Async mapping and dependency boundary are explicit.
