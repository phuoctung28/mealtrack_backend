---
phase: 2
title: "Bound Notification Workloads"
status: pending
priority: P1
effort: "2-3 days"
dependencies: [1]
---

# Phase 2: Bound Notification Workloads

## Context Links

- [Overview](./plan.md)
- [Batching research](./research/researcher-02-batching-delivery-and-rollout.md)
- `src/cron/push.py`
- `src/infra/services/daily_context_precompute_service.py`
- `src/infra/services/cron_notification_dispatch_service.py`

## Overview

Turn push precomputation, notification dispatch, trial reminders, and cleanup into bounded, restartable workload steps. Preserve existing service behavior and cron entrypoints during migration while eliminating whole-table reads and unbounded queue claims.

## Key Insights

- Daily precompute currently loads all matching users, tokens, profiles, calories, and preferences into memory. The existing “any row exists” sentinel is not valid once work is paginated.
- Notification claiming already uses `SKIP LOCKED`, but without a limit; Firebase calls are synchronous and can block the event loop.
- The worker has two bounded lanes. Push dispatch may overlap one maintenance batch, while precompute, trial scheduling, and cleanup remain mutually exclusive.

## Requirements

- Use stable user-ID keyset pagination with a frozen upper bound. Write-side handlers must directly reschedule when eligibility changes behind the cursor, including first active-token registration.
- Track precompute by logical timezone/date run and durable cursor, not by the presence of one result row.
- Bound every claim and cleanup statement; commit claims before provider calls.
- Preserve at-least-once delivery and existing notification row identity while fixing per-recipient provider result mapping.
- Keep compatibility adapters so Render cron can be restored during staged rollout.
- Permit at most one dispatch batch plus one maintenance batch; never run two batches of the same notification subjob.

## Architecture

The worker exposes an urgent dispatch lane and one maintenance lane. Precompute checkpoints `(upper_bound_user_id, last_user_id)`; dispatch fences and commits claims, rehydrates current tokens, then performs provider I/O while maintenance may progress. Precompute, trial, and cleanup never overlap each other. Phase 4 owns admission and fairness.

## Related Code Files

### Modify

- `src/cron/push.py`
- `src/infra/services/daily_context_precompute_service.py`
- `src/infra/services/cron_notification_dispatch_service.py`
- `src/infra/services/cron_trial_push_service.py`
- `src/infra/repositories/subscription_repository_async.py`
- `src/infra/services/firebase_service.py`
- `src/infra/database/models/notification/notification.py`
- `src/app/handlers/command_handlers/register_fcm_token_command_handler.py`
- `tests/unit/infra/test_daily_context_precompute_service.py`
- `tests/unit/infra/test_cron_notification_dispatch_service.py`
- Relevant dependency/container wiring under `src/`

### Create

- `migrations/versions/20260808000002_add_notification_claim_ownership.py`
- `tests/integration/postgres/test_notification_claim_batching.py`

## Implementation Steps

1. Add a migration/model change for notification `claim_token`, `claim_epoch`, `claimed_at`, and `claim_expires_at`, plus the reclaim index. Mixed-version compatibility must leave old pending rows claimable; every result mutation and stale recovery must be owner/epoch conditional and assert affected rows.
2. Fetch at most 100 eligible users after a stable user-ID cursor and at/below a frozen upper bound. Return `next_cursor`/`has_more`; add the final query-shaped index after `EXPLAIN`. On first active-token registration or other eligibility change behind a live cursor, invoke the existing per-user reschedule path.
3. Refactor precompute into a bounded timezone/date scan. Remove the any-row sentinel; checkpoint every examined user and complete only after the final page. Batch-load weekly-budget/consumption inputs or enforce a measured query budget; add a query-count regression test for 100 users.
4. Claim at most 100 due, unexpired notifications with deterministic ordering. Commit ownership before provider I/O. Rehydrate active tokens for claimed user IDs at dispatch time; never treat `context.fcm_tokens` as recipient authority.
5. Preserve `(row_id, token)` mapping across each FCM chunk. Mark a row sent only when at least one current token succeeds; classify all-token failure for retry/permanent failure. Keep `notification_ids` recipient-scoped so no token receives another user's row IDs. Offload synchronous SDK calls via `asyncio.to_thread` with the bounded executor/deadline policy from Phase 4.
6. Bound trial scans to 100 and cleanup to 500. Cleanup must never delete a live claim: restrict to terminal rows or expired unclaimed/expired-lease rows, with affected-row checks.
7. Keep `src/cron/push.py` as a compatibility wrapper over the same bounded methods and claims. The worker's single push flag enables all four steps; do not disable the cron until all four worker steps are active.
8. Test empty/final/multi-page cursors, eligibility gained behind cursor, query count, restart, owner/epoch loss, immediate old-schedule reclaim prevention, token deactivation, mixed per-token outcomes, recipient-scoped IDs, cleanup/send race, event-loop responsiveness, strict caps, two PostgreSQL claimers, dispatch-plus-precompute overlap, maintenance mutual exclusion, and no same-job double batch.

## Todo List

- [ ] Add stable keyset repository queries.
- [ ] Add notification row ownership and claim-expiry migration.
- [ ] Make daily precompute cursor-based and resumable.
- [ ] Limit dispatch, trial, and cleanup claims.
- [ ] Offload blocking Firebase calls.
- [ ] Rehydrate active recipients and preserve row/token outcome mapping.
- [ ] Keep the push cron compatibility path.
- [ ] Cover concurrency, restart, and partial-failure cases.
- [ ] Prove two-lane overlap without same-job or maintenance overlap.

## Success Criteria

- [ ] No notification workload fetches or claims more than its configured cap.
- [ ] Precompute resumes after a crash without skipping users or treating a partial day as complete.
- [ ] Concurrent worker/cron claimers do not own the same queue row.
- [ ] A newly claimed overdue row is not immediately considered stale, and cleanup cannot delete it.
- [ ] Provider I/O occurs after the claim transaction closes.
- [ ] Existing notification behavior and idempotency keys remain backward compatible.
- [ ] Current-token and per-recipient payload tests prevent stale delivery/cross-recipient IDs.
- [ ] Dispatch continues during bounded precompute while total concurrency remains at or below two.

## Risk Assessment

- **Pagination gaps:** freeze an upper bound and route eligibility mutations behind the cursor through direct per-user rescheduling.
- **FCM accepted but response lost:** at-least-once retry can rarely duplicate a push; this is the explicitly accepted ambiguity.
- **Push starvation:** Phase 4 reserves the urgent lane for dispatch and selects the oldest-overdue maintenance job; yielding alone is not treated as fairness.

## Security Considerations

Do not log device tokens or message payloads. Preserve existing eligibility/privacy filters for trial and push notifications. Validate cursor and limit server-side rather than accepting arbitrary values.

## Next Steps

Phase 4 registers these bounded steps in the portable worker, colocated initially. The old push cron stays available until Phase 5 verifies production-like behavior.
