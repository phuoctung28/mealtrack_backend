# Catalog Recommendation Response Localization

## Context

Catalog-backed recommendation responses were canonical English even though the backend already parsed `Accept-Language` and provided a DeepL text translation service.

## Change

- Added an application-layer response localizer that batches and deduplicates display text per response.
- Localized meal names, cuisines, descriptions, and ingredient display names after CQRS reads.
- Kept catalog data, persisted recommendation plans, units, nutrition, IDs, scores, and state immutable and canonical.
- Added canonical-English fallback for missing DeepL configuration, provider failures, and short provider responses.

## Evidence

- 109 recommendation-focused tests passed.
- Ruff, mypy, import-layer contracts, route registration smoke test, and documentation validation passed.

## Decision

`Accept-Language` is authoritative for these endpoints. User-profile language is not consulted, and no translated catalog data is persisted.
