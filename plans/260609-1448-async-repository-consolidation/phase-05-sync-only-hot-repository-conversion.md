---
phase: 5
title: "Sync-Only Hot Repository Conversion"
status: completed
priority: P1
effort: "5-7 days"
dependencies: [4]
---

# Phase 5: Sync-Only Hot Repository Conversion

## Overview

Convert sync-only DB-backed repositories that sit on hot or fragile paths: food reference, meal translation, pgvector cache, and pending image queue.

## Requirements

- Functional: repositories use `AsyncSession`.
- Functional: repositories do not commit internally.
- Functional: pgvector cache failure still falls back safely and does not poison later request work.
- Functional: pending image queue writes preserve behavior.
- Non-functional: keep external API and service responses unchanged.

## Architecture

Prefer explicit async repository classes over generic adapter layers. Keep pure SQL helper functions only if they are driver-neutral.

## Related Code Files

- Modify/Rename: `src/infra/repositories/food_reference_repository.py`
- Modify/Rename: `src/infra/repositories/meal_translation_repository.py`
- Modify/Rename: `src/infra/repositories/pgvector_meal_image_cache_repository.py`
- Modify/Rename: `src/infra/repositories/pending_meal_image_repository.py`
- Modify: `src/api/dependencies/meal_image_cache.py`
- Modify: `src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py`
- Modify: `src/domain/services/meal_suggestion/suggestion_orchestration_service.py`
- Modify: related unit/integration tests

## Implementation Steps

1. Convert food reference methods to accept/inject `AsyncSession`.
2. Convert meal translation persistence to async session/UoW ownership.
3. Convert pending image queue repository to async methods and flush-only writes.
4. Convert pgvector cache repository to async SQLAlchemy.
5. Preserve cache lookup fallback-to-miss behavior with explicit transaction recovery.
6. Update dependencies and services to use async repositories.
7. Run targeted tests for food, translation, pending image, and pgvector cache.

## Success Criteria

- [x] Hot repositories have async implementations.
- [x] No hot repository commits internally.
- [x] Pgvector cache query failure does not produce later `InFailedSqlTransaction`.
- [x] Food lookup and meal suggestion flows preserve output.
- [x] Pending image queue request-path behavior preserve behavior.

## Progress Notes

- Added `AsyncPgvectorMealImageCacheRepository` using `AsyncSession`.
- Added `AsyncPendingMealImageRepository` using `AsyncSession`.
- Async hot repositories flush writes and do not commit internally.
- Pgvector async batch query rolls back failed cache transactions so the request can fall through to image search.
- Sync repositories remain for scripts and legacy integration tests until the operational/test migration phases.
- Added `AsyncFoodReferenceRepository` with hot lookup/upsert methods.
- `NutritionLookupService` and `IngredientNutritionResolver` now support async food-reference repositories while preserving legacy sync repository compatibility.
- `AsyncUnitOfWork` exposes `food_references` for future session-owned wiring.
- Added `AsyncMealTranslationRepository` and converted the meal translation port to async-shaped methods.
- `DeepLMealTranslationService` now awaits async meal translation repositories while preserving legacy sync repository compatibility.
- `AsyncUnitOfWork` exposes `meal_translations` for future session-owned wiring.

## Risk Assessment

Risk: pgvector raw SQL bind behavior differs between psycopg2 and asyncpg.

Mitigation: use typed SQLAlchemy binds and targeted integration tests against PostgreSQL.
