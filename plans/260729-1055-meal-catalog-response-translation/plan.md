---
title: Meal catalog response translation
description: >-
  Translate catalog-backed meal recommendation text at response time using the
  request language while keeping canonical catalog data in English.
status: completed
priority: P2
effort: 1d 5h
branch: delivery
tags:
  - feature
  - backend
  - api
blockedBy: []
blocks: []
created: '2026-07-29'
createdBy: 'ck:plan'
source: skill
---

# Meal catalog response translation

## Overview

Add locale-aware presentation for catalog-backed meal recommendation endpoints. Canonical `meal_catalog` rows and persisted recommendation plans remain English and unchanged; response mapping translates user-facing catalog text using the existing validated `Accept-Language` request state.

Verified reusable seams:

- `AcceptLanguageMiddleware` supports `en`, `vi`, `es`, `fr`, `de`, `ja`, `zh` and defaults to English.
- `DeepLTextTranslationService` already batches text and returns originals on provider failure.
- `meal_recommendation_route_support.py` is the shared projection seam for all recommendation response shapes.
- `CatalogMeal` is frozen and calories are backend-derived, so localization must create projections rather than mutate domain/catalog data.

Scope: translate meal `name`, `cuisine`, `description`, and ingredient `display_name`. Preserve IDs, meal types, units, quantities, macros, calories, scores, ordering, and state. No translation columns, migration, client language override, or persisted translated content.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Localization contract and translation boundary](./phase-01-localization-contract-and-translation-boundary.md) | Completed |
| 2 | [Implement catalog response translation](./phase-02-implement-catalog-response-translation.md) | Completed |
| 3 | [Verification and documentation](./phase-03-verification-and-documentation.md) | Completed |

## Dependencies

- No unfinished plan blocks this work. The current four-table catalog response contract is the integration target.
- Runtime dependency: configured `DEEPL_API_KEY`; without it, responses remain canonical English.

## Success Criteria

- Non-English requests receive translated catalog text across every recommendation response shape.
- English, unsupported, missing, provider-error, and partial-result paths remain safe.
- Translation is batched/deduplicated and does not alter ranking, persistence, cache keys, nutrition, or IDs.
- Focused tests, lint/type checks, and API documentation are complete.

## Unresolved Questions

None.
