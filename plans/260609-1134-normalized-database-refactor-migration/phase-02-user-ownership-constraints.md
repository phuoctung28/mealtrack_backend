---
phase: 2
title: "User ownership constraints"
status: completed
priority: P1
effort: "4-6 days"
dependencies: [1]
---

# Phase 2: User ownership constraints

## Context Links

- Standards: `docs/standards/db-api.md`
- Review finding: inconsistent user ownership

## Overview

Add database-enforced ownership for user-owned rows. Clean orphans first, then add FKs and indexes in safe order.

## Key Insights

- Some tables already have `ForeignKey("users.id")`; others only store string `user_id`.
- `saved_suggestions.user_id` is `String(128)`, but `/v1/saved-suggestions` now receives canonical `users.id` from `get_current_user_id`; audit legacy rows before narrowing/adding FK.
- Delete-account flow soft-deletes/anonymizes users, so cascade policy must match business retention.

## Requirements

- Functional: user-owned private tables reference `users.id`.
- Functional: migration handles orphans deterministically.
- Non-functional: do not lock hot tables longer than needed; use staged constraints where needed.

## Architecture

Use data audit/backfill migration before adding constraints. Private product data can cascade. Accounting/referral data is not part of this phase except policy notes.

## Related Code Files

| Action | File |
|---|---|
| Modify | `src/infra/database/models/notification/notification_preferences.py` |
| Modify | `src/infra/database/models/notification/user_fcm_token.py` |
| Modify | `src/infra/database/models/weekly/weekly_macro_budget.py` |
| Modify | `src/infra/database/models/cheat_day/cheat_day.py` |
| Modify | `src/infra/database/models/meal/meal.py` |
| Modify | `src/infra/database/models/saved_suggestion.py` |
| Create | `migrations/versions/YYYYMMDDHHMMSS_add_user_owner_foreign_keys.py` |
| Modify/Add | `tests/integration/test_delete_account_api.py` |
| Create | `tests/migrations/test_user_owner_constraints.py` |

## Implementation Steps

1. Add a data audit query/migration section for each target table:
   - `notification_preferences`
   - `user_fcm_tokens`
   - `weekly_macro_budgets`
   - `cheat_days`
   - `meal`
   - `saved_suggestions` after auditing/fixing legacy outliers.
2. For rows whose `user_id` has no matching `users.id`, choose deterministic handling:
   - private transient rows: delete or mark inactive;
   - meal/history rows: quarantine report table or abort migration if unexpected;
   - saved suggestions: repair outliers, then migrate to canonical `users.id` FK.
3. Add FKs with intentional `ondelete`:
   - preferences/tokens/weekly/cheat/meal: likely `CASCADE`;
   - saved suggestions: `CASCADE` after ID fix.
4. Keep or replace indexes so FK columns stay indexed without duplicate coverage.
5. Add tests for FK enforcement, orphan migration behavior, and delete-account ownership behavior.
6. Run targeted migrations/tests, then full migration graph test.

## Test Scenario Matrix

| Scenario | Test |
|---|---|
| Valid user-owned rows survive migration | migration test fixture |
| Orphan transient rows handled deterministically | migration test fixture |
| FK rejects future orphan insert | DB integration assertion |
| Delete account does not leave private orphan rows | integration delete-account test |
| Saved suggestion legacy outliers are audited before FK | explicit test or precondition guard |

## Success Criteria

- [x] Private user-owned tables have FK constraints to `users.id`.
- [x] Orphan handling documented in migration comments.
- [x] No duplicate/redundant user_id indexes introduced.
- [x] `saved_suggestions.user_id` is canonical `users.id` before FK.

## Risk Assessment

Medium risk. Existing orphan rows or legacy Firebase UID values can break migration. Mitigation: preflight queries, staged migration, and repair saved-suggestion outliers before adding FK.

## Security Considerations

FKs improve account-deletion integrity. Cascade private logs/preferences/suggestions; retain or anonymize accounting/audit records.

## Next Steps

With ownership enforced, normalize source-of-truth JSON starting with user profile preferences.
