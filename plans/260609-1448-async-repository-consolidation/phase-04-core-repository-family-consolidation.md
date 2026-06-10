---
phase: 4
title: "Core Repository Family Consolidation"
status: completed
priority: P1
effort: "5-7 days"
dependencies: [3]
---

# Phase 4: Core Repository Family Consolidation

## Overview

Promote existing async repository families as canonical and remove consumer reliance on their sync counterparts.

## Requirements

- Functional: core repository writes are transaction-owned by `AsyncUnitOfWork`.
- Functional: async repositories preserve domain mapping and query behavior.
- Functional: sync repository consumers are removed before sync files are deleted.
- Non-functional: no API response shape change.

## Architecture

Canonical repositories:

- `AsyncMealRepository`
- `AsyncUserRepository`
- `AsyncSubscriptionRepository`
- `AsyncWeeklyBudgetRepository`
- `AsyncSavedSuggestionDbRepository`
- `AsyncCheatDayRepository`
- `AsyncNotificationRepository`

## Related Code Files

- Modify: `src/infra/repositories/*_async.py`
- Modify: `src/infra/repositories/notification/*.py` or replace with async helpers
- Modify: `src/infra/database/uow_async.py`
- Modify: command/query handlers using core repositories
- Delete later: sync counterparts after phase 8 verification

## Implementation Steps

1. Compare sync vs async core repository method coverage.
2. Add any missing async methods required by active consumers.
3. Move notification helper operations into `AsyncNotificationRepository` or async helper modules.
4. Confirm all core repo writes use flush-only behavior.
5. Update consumers to canonical async repositories.
6. Run core repository and handler tests.

## Success Criteria

- [x] Async repository methods cover all active core runtime use cases.
- [x] Core sync repositories have no runtime consumers.
- [x] Repository-level commit calls are gone from canonical core repos.
- [x] Notification token/preference behavior remains compatible.

## Progress Notes

- `AsyncSubscriptionRepository` now implements `SubscriptionRepositoryPort`.
- Added async `find_expiring_soon` and `find_expiring_in_window` coverage for operational subscription flows.
- Added focused unit tests for async subscription expiry-window queries and port contract satisfaction.
- Expanded `AsyncFoodReferenceRepository` parity with barcode upsert/cache writes so barcode lookup no longer needs the sync singleton repository in production event-bus wiring.
- Added an async food-reference UoW adapter for singleton services that must not hold an `AsyncSession`.
- Added an async meal-translation UoW adapter for the DeepL meal translation singleton.
- Added `promo_codes` and `referrals` to `AsyncUnitOfWork` and its port.
- Migrated promo-code, unified-code, referral, and webhook side-effect handlers to use canonical UoW-owned promo/referral repositories.
- Added an architecture guard that blocks runtime handler/route/service code from importing or constructing promo/referral repositories directly.
- Deleted the remaining core sync repository modules after static runtime checks confirmed no active consumers remained.
- Canonical async repositories now rely on UoW-owned transactions; the async pgvector cache keeps explicit rollback only for transaction recovery after pgvector failures.

## Risk Assessment

Risk: sync and async repositories may not have identical behavior.

Mitigation: add parity tests for high-value methods before deleting sync consumers.
