---
phase: 6
title: "Mobile Stale-While-Revalidate"
status: completed
priority: P1
effort: "2-3d"
dependencies: [2, 5]
mode: tdd
---

# Phase 6: Mobile Stale-While-Revalidate

## Overview

Render the last user-scoped plan summary immediately, refresh in the background, load detail on demand, and patch target slots from deltas.

## Requirements

- Cache `{schema_version, user_scope, cached_at, plan}` in SharedPreferences; no secrets.
- Return valid cache synchronously and show `isRefreshing`, not blank `isLoading`.
- Remove corrupt, unknown-version, wrong-user, or expired-plan cache; offline refresh preserves valid cache.
- No-cache behavior keeps existing loading/error behavior.
- Create/get consume the compact plan contract; swap/log consume the changed-slot contract; details/alternatives load lazily.
- Late refresh cannot overwrite a newer mutation.
- Pending request IDs survive failure and clear only after delta application plus cache persistence.

## File Inventory

All paths are under `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai`.

| Action | Files |
|---|---|
| Modify | `lib/core/network/api_service.dart` and generated Retrofit output |
| Modify | recommendation API models and generated Freezed/JSON output |
| Modify | remote data source and mapper |
| Add | `lib/features/meal_recommendation/data/datasources/meal_recommendation_cache_data_source.dart` |
| Modify | domain repository and repository implementation |
| Modify | `application/providers/meal_recommendation_controller.dart` |
| Modify | detail screen, alternatives sheet, and slot-card providers/widgets |
| Extend | repository, controller, detail, alternatives, and plan-deck tests |

## Function And Interface Checklist

- Repository separates cached read, remote refresh, lazy detail, and delta mutations.
- Controller state separates initial loading, refresh, and per-slot mutation.
- Delta patch verifies plan/slot/version and replaces exactly one slot.
- Cache validates schema and user scope before domain mapping.
- Generate Retrofit/Freezed output only after handwritten contract tests fail as expected.

## Tests Before

1. Valid payload round-trips; corrupt/version/wrong-user/expired entries are discarded.
2. First state contains cached plan and begins refresh without blanking content.
3. Success replaces only older cache; failure preserves it; 404 clears stale cache and regenerates.
4. Delta patches exactly one slot and preserves the other eight.
5. Late refresh cannot undo a completed mutation.
6. Failed mutation keeps prior plan/request ID; success clears ID after cache write.
7. Lazy detail/alternatives show local loading/retry without blanking home.

## Refactor

1. Replace current models with compact-plan, changed-slot, and slot-detail models/mappings.
2. Extract typed cache serialization.
3. Bootstrap cache, then remote refresh.
4. Add a state generation/version guard around refresh/mutations.
5. Patch one slot; preserve full meal data for logged-meal projection.
6. Load ingredients/alternatives only when opened.

## Tests After And Regression Gate

```bash
/Users/alexnguyen/flutter/bin/flutter test test/features/meal_recommendation/data/repositories/meal_recommendation_repository_impl_test.dart test/features/meal_recommendation/application/providers/meal_recommendation_controller_test.dart test/features/meal_recommendation/presentation/widgets/recommended_meal_alternatives_sheet_test.dart test/features/meal_recommendation/presentation/widgets/recommended_meal_plan_deck_test.dart
/Users/alexnguyen/flutter/bin/dart analyze lib/features/meal_recommendation test/features/meal_recommendation
```

## Success Criteria

- [x] Returning users see cached recommendations before network completes.
- [x] Offline/slow refresh does not blank a valid plan.
- [x] Detail and alternatives load only on demand.
- [x] Swap/log patch one slot and preserve idempotent retry.
- [x] Generated code, focused tests, and analysis are clean.

## Completion Evidence

- Added slot-detail API model and Retrofit methods for compact/detail/delta contracts.
- Added user-scoped SharedPreferences plan cache and synchronous cached-plan read.
- Controller now renders cached plan while refreshing and patches exactly one slot from swap/log responses.
- Regenerated Freezed/JSON/Retrofit output.
- Focused Dart analysis and meal recommendation controller/widget tests pass.

## Risks And Security

Clear user-scoped cache on logout/account switch. Cached meals are display data, never authorization or calorie authority.

## Next Steps

Ship backend and mobile as one unreleased feature contract after integration tests pass.
