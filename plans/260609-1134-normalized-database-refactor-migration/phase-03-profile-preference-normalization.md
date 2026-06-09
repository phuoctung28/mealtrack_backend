---
phase: 3
title: "Profile preference normalization"
status: completed
priority: P1
effort: "1-2 weeks"
dependencies: [1, 2]
---

# Phase 3: Profile preference normalization

## Context Links

- Model: `src/infra/database/models/user/profile.py`
- Mapper: `src/infra/mappers/user_mapper.py`
- Repository: `src/infra/repositories/user_repository_async.py`

## Overview

Normalize repeated profile preference arrays into child/reference tables while preserving existing domain/API arrays during rollout.

## Key Insights

- `UserProfile` stores `dietary_preferences`, `health_conditions`, `allergies`, `pain_points`, `referral_sources`, and `training_types` as JSON.
- Existing domain/API expects arrays, so mapper/repository compatibility is the right boundary.

## Requirements

- Functional: API/domain still return arrays.
- Functional: normalized tables become source of truth for new writes.
- Non-functional: idempotent backfill, no user-visible onboarding regression.

## Architecture

Add normalized profile attribute rows grouped by type. Keep stable arrays at API/domain edge. Read normalized first, fallback to legacy JSON until contract phase.

Suggested tables:

- `user_profile_preferences(profile_id, preference_type, value, position)`
- Or specific tables if stronger constraints are needed:
  - `user_dietary_preferences`
  - `user_health_conditions`
  - `user_allergies`
  - `user_pain_points`
  - `user_training_types`
  - `user_referral_sources`

Recommendation: use one typed child table only if validation lists remain flexible; use specific tables if enum/check constraints differ by type.

## Related Code Files

| Action | File |
|---|---|
| Create | `src/infra/database/models/user/profile_preference.py` |
| Modify | `src/infra/database/models/user/__init__.py` |
| Modify | `src/infra/database/models/__init__.py` |
| Modify | `src/infra/mappers/user_mapper.py` |
| Modify | `src/infra/repositories/user_repository_async.py` |
| Modify | `src/infra/repositories/user_repository.py` if sync path remains active |
| Create | `migrations/versions/YYYYMMDDHHMMSS_normalize_user_profile_preferences.py` |
| Modify/Add | `tests/unit/domain/services/test_user_profile_service.py` |
| Modify/Add | `tests/integration/api/test_user_profiles_api.py` |
| Create | `tests/integration/infra/repositories/test_user_profile_preferences.py` |

## Implementation Steps

1. Tests before: capture current profile read/write behavior for arrays, null legacy JSON, unknown preferences, and ordering.
2. Add normalized model/table with FK to `user_profiles.id`, cascade delete, unique `(profile_id, preference_type, value)`, and `(profile_id, preference_type, position)` index if order matters.
3. Backfill from each JSON array, skipping nulls, coercing strings, deduping by normalized value, preserving first order.
4. Update `UserProfileMapper.to_domain` to prefer loaded normalized rows, fallback to legacy JSON.
5. Update `UserProfileMapper.to_persistence` or repository save/update to dual-write normalized rows and legacy JSON.
6. Eager-load/selectin-load preference rows in user/profile reads.
7. Add cache invalidation if profile cache keys depend on these values.
8. Keep old JSON columns until phase 7 contract.

## Test Scenario Matrix

| Scenario | Test |
|---|---|
| Legacy JSON-only profile reads unchanged | mapper/repository test |
| Normalized profile reads arrays correctly | repository integration |
| Update writes normalized + legacy JSON | repository integration |
| Duplicate/null malformed JSON does not crash backfill | migration test |
| Onboarding endpoints preserve response shape | API integration |

## Success Criteria

- [x] New writes store profile arrays in normalized child rows.
- [x] Existing API/domain contracts unchanged.
- [x] Legacy rows still read through fallback.
- [x] Migration can be rerun safely after partial failure.

## Risk Assessment

Medium risk. Profile values drive suggestions, prompts, and onboarding. Mitigation: mapper-level fallback and broad tests around onboarding/profile reads.

## Security Considerations

Health conditions/allergies are sensitive user data. Keep cascade/delete behavior aligned with account deletion and do not log raw values in migration errors.

## Next Steps

Apply the same expand-migrate-contract pattern to hydration, where current table semantics are overloaded.
