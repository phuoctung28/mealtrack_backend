---
phase: 7
title: "Read cutover indexes and summaries"
status: completed
priority: P2
effort: "1 week"
dependencies: [3, 4, 5, 6]
---

# Phase 7: Read cutover indexes and summaries

## Context Links

- Cache invalidation: `src/app/services/cache_invalidation_service.py`
- Daily query handlers: `src/app/handlers/query_handlers/`
- DB standards: `docs/standards/db-api.md`

## Overview

Flip reads to normalized tables, add final query indexes, and introduce read models only where repeated hot queries justify them.

## Key Insights

- Read models amplify drift if source tables are not stable.
- Many current queries are bounded by `(user_id, date)` and can work with compound indexes before materialized summaries.

## Requirements

- Functional: all migrated domains read normalized data first.
- Functional: fallback paths remain for one release unless product decides otherwise.
- Non-functional: index additions are evidence-based; no broad over-indexing.

## Architecture

Use feature/config flags for read cutovers if deployment risk is high. Add indexes after final query shape is known. Add daily summaries only for proven hot paths.

Likely index candidates:

- `hydration_entries(user_id, logged_at)`
- `saved_suggestions(user_id, saved_at)` retained/verified
- `saved_suggestion_items(saved_suggestion_id, position)`
- `meal_instruction_steps(meal_id, position)`
- `user_profile_preferences(profile_id, preference_type, position)`
- notifications due partial index review

Potential read model:

- `daily_user_nutrition_summaries(user_id, local_date, calories, protein, carbs, fat, fiber, sugar, water_ml, movement_calories, source_updated_at)`

## Related Code Files

| Action | File |
|---|---|
| Modify | `src/app/handlers/query_handlers/get_daily_macros_query_handler.py` |
| Modify | `src/app/handlers/query_handlers/get_daily_breakdown_query_handler.py` |
| Modify | `src/app/handlers/query_handlers/get_bulk_activities_query_handler.py` |
| Modify | `src/app/handlers/query_handlers/get_nutrition_bulk_query_handler.py` |
| Modify | `src/app/services/cache_invalidation_service.py` |
| Optional Create | `src/infra/database/models/daily_user_nutrition_summary.py` |
| Optional Create | `src/infra/repositories/daily_summary_repository_async.py` |
| Create | `migrations/versions/YYYYMMDDHHMMSS_add_normalized_read_indexes.py` |
| Optional Create | `migrations/versions/YYYYMMDDHHMMSS_add_daily_user_nutrition_summaries.py` |

## Implementation Steps

1. Verify each normalized domain has at least one production-safe release of dual-write/fallback.
2. Switch repository/query reads to normalized-first as default. Keep legacy fallback behind code path and tests.
3. Add final compound/partial indexes based on actual query filters. Use `EXPLAIN` for heavyweight/high-write tables.
4. Review cache invalidation to ensure normalized write paths invalidate the same API cache keys.
5. Add daily summary read model only if request-time daily/macros/activity queries show repeated hot-path cost.
6. If adding read model, rebuild from normalized source tables and treat it as derived only.
7. Plan contract migrations to remove old JSON columns in a later release, not immediately.

## Test Scenario Matrix

| Scenario | Test |
|---|---|
| Normalized rows read without legacy columns | repository/query test |
| Legacy fallback still works | repository/query test |
| Cache invalidation after normalized writes | cache tests |
| Index names exist in migrations/models | metadata/migration test |
| Daily summary rebuild matches source tables | optional integration test |

## Success Criteria

- [x] Normalized tables are primary read source for migrated domains.
- [x] Legacy fallback remains tested until contract release.
- [x] Indexes match query patterns and do not duplicate coverage.
- [x] Any read model is clearly derived/rebuildable.

## Risk Assessment

Medium. Read cutovers can cause subtle mismatches. Mitigation: dual-read comparison tests and short compatibility window before dropping legacy columns.

## Security Considerations

Derived summaries must not outlive user deletion/retention rules. Cascade or rebuild policy must be explicit.

## Next Steps

Prepare rollout, rollback, and final verification gates.
