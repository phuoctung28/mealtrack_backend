---
phase: 2
title: Implement catalog response translation
status: completed
priority: P2
effort: 1d
dependencies:
  - 1
---

# Phase 2: Implement catalog response translation

## Overview

Implement request-language localization in the existing recommendation response path. Translation is presentation-only and transparent when DeepL is unavailable.

## Requirements

- All recommendation response shapes use the same localization seam.
- No domain/catalog object is mutated.
- Provider work is skipped for English and deduplicated for repeated strings.

## Architecture

The route obtains `get_request_language(request)` and the existing text translation dependency. After CQRS/domain results are loaded, an async localizer reconstructs translated `CatalogMeal` projections, then existing Pydantic response builders serialize them. Ranking, snapshot refresh, persistence, and analytics remain untouched. Avoid cross-request caching initially; add only a bounded content-hash/language cache if measured need justifies it.

## Related Code Files

- Modify: `src/api/routes/v1/meal_recommendation_route_support.py` — async localizer and translated projections.
- Modify: `src/api/routes/v1/meal_recommendations.py` — request language and translator dependency for create/get/detail/swap/log/skip.
- Modify: `src/api/base_dependencies.py` only if a narrowly scoped localizer dependency is required.
- Create only if needed: `src/app/services/catalog_meal_response_localizer.py`.
- Modify: `tests/unit/api/test_meal_recommendation_http_contract.py`, `tests/unit/api/test_meal_recommendations_route.py`.
- Create only if needed: `tests/unit/app/services/test_catalog_meal_response_localizer.py`.

## Implementation Steps

1. Write fake-translator tests that record batches and return deterministic output.
2. Implement deduplication, empty-description handling, frozen projection reconstruction, and safe padding/fallback.
3. Make mapping helpers async or delegate to an async localizer; update all six route paths consistently.
4. Preserve units, quantities, macros, calories, IDs, scores, and recommendation state exactly.
5. Reuse the existing service fallback; do not add duplicate route-level error logging.

## Success Criteria

- [x] Supported non-English requests localize names, cuisine, descriptions, and ingredient names.
- [x] English/missing/unsupported/provider-failure paths return canonical content successfully.
- [x] Repeated strings translate once per response and no domain object changes.
- [x] No migration or catalog write path changes.
