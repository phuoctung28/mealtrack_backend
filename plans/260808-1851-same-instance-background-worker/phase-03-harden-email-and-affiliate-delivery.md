---
phase: 3
title: "Harden Email and Affiliate Delivery"
status: pending
priority: P1
effort: "2 days"
dependencies: [1]
---

# Phase 3: Harden Email and Affiliate Delivery

## Context Links

- [Overview](./plan.md)
- [Batching and delivery research](./research/researcher-02-batching-delivery-and-rollout.md)
- `src/cron/email.py`
- `src/cron/affiliate_outbox.py`
- `src/infra/adapters/resend_email_adapter.py`

## Overview

Prepare lifecycle email and affiliate outbox for safe worker execution, but keep both execution flags false because neither workload currently runs. Email gains a durable per-recipient claim plus provider idempotency; affiliate gains explicit processing ownership. Neither contributes to initial notification capacity tests.

## Key Insights

- Lifecycle email currently performs check, provider send, and log as separate actions with no unique claim, so overlapping processes can both send.
- The installed Resend SDK accepts an options object containing `idempotency_key`; the email port must propagate this without changing unrelated email semantics.
- Affiliate claim currently updates only `locked_at` while leaving status `pending`; after commit, another claimer can immediately select the same row.

## Requirements

- Lifecycle email starts within 15 minutes of 09:00 UTC and processes no more than 25 recipients per step.
- A deterministic user/template/date delivery key prevents concurrent logical duplicates; a separate daily scan cursor ensures later recipients cannot starve. The delivery key is sent to Resend on retry.
- Affiliate rows transition atomically from `pending` to `processing`, carry an owner/lease, and are reclaimable after expiry.
- No database transaction spans Resend or affiliate-network I/O.
- Existing callers of the email port remain source-compatible or are migrated explicitly and tested.
- `BACKGROUND_JOB_EMAIL_ENABLED` and `BACKGROUND_JOB_AFFILIATE_ENABLED` remain false through the initial notification rollout; disabled workloads create no claims or provider calls.

## Architecture

Each lifecycle type has one daily cursor-backed scan run; every examined recipient advances its cursor, including suppressed recipients. A candidate then creates/claims a delivery run keyed by lifecycle type, user, and scheduled date. The transaction commits; Resend receives the same key; only a real `sent` result completes it. Affiliate uses its queue-native status/owner fields only—no duplicate aggregate job-run state.

## Related Code Files

### Modify

- `src/cron/email.py`
- `src/cron/affiliate_outbox.py`
- `src/infra/services/cron_lifecycle_email_service.py`
- `src/domain/services/email_service.py`
- `src/domain/ports/email_service_port.py`
- `src/infra/adapters/resend_email_adapter.py`
- `src/infra/database/models/email_log.py`
- `src/infra/database/models/affiliate_event_outbox.py`
- `src/infra/repositories/affiliate_event_outbox_repository.py`
- `src/infra/services/affiliate_outbox_dispatch_service.py`
- `tests/unit/infra/services/test_cron_lifecycle_email_service.py`
- `tests/unit/infra/services/test_affiliate_outbox_dispatch_service.py`
- All production, fake, and test implementations/callers of `send_email`

### Create

- `migrations/versions/20260808000003_add_affiliate_outbox_claim_ownership.py`
- `tests/unit/infra/repositories/test_affiliate_outbox_claims.py`
- `tests/integration/postgres/test_affiliate_outbox_concurrency.py`

## Implementation Steps

1. Inventory `EmailServicePort.send_email` implementations/callers. Add an optional keyword-only idempotency key at the port/adapter boundary and to only `EmailService.send_reengagement_email` and `send_trial_expiring_email`; forward it unchanged as Resend request options. Keep welcome, cancellation, web-funnel, and other callers unchanged.
2. Refactor each lifecycle candidate query into deterministic keyset pages of 25 backed by one daily scan run/cursor. Advance the cursor for every examined row, even if suppressed/owned, and complete only after the final page. Batch-load the existing seven-day `EmailLog` suppression set for the page; preserve that business rule in addition to per-delivery keys.
3. Before sending, atomically create/claim `lifecycle:{type}:{user_id}:{scheduled_date}`. Commit, call Resend outside the transaction with that exact key, then owner/epoch-conditionally complete or retry. Distinguish `sent`, `disabled/deferred`, and `failed`; `EMAIL_ENABLED=false` must not create a sent log or consume the claim.
4. Make the affiliate migration mandatory: add processing owner token, claim epoch, claim expiry, safe constraints/backfill, and due/reclaim indexes. A bounded claim atomically transitions `pending` to `processing`; stale claims are reclaimable and every result mutation is owner/epoch conditional.
5. Keep affiliate provider I/O after claim commit; mark `sent`, retry, or dead-letter with the existing attempt policy and unique downstream `event_id`. Use native queue state, not an aggregate scheduler run.
6. Retain email and affiliate cron wrappers over the same operations. Register their workloads behind default-false flags; when disabled they must not consume a workload slot, create a run/claim, or call a provider.
7. Test multi-page email scans, seven-day suppression, disabled flags, exact Resend key propagation/retry, response loss, concurrent claimers, stale takeover, old-owner rejection, poison rows, and strict caps/query counts. Activation tests must also prove the global two-slot and one-batch-per-job limits.

## Todo List

- [ ] Propagate optional Resend idempotency keys through the email port.
- [ ] Add atomic lifecycle-email schedule claims and bounded pages.
- [ ] Add durable lifecycle scan cursors and preserve seven-day suppression.
- [ ] Distinguish sent, disabled/deferred, and failed email outcomes.
- [ ] Add real affiliate processing ownership and stale recovery.
- [ ] Preserve compatibility cron wrappers.
- [ ] Keep both workload flags dormant during notification rollout.
- [ ] Test provider ambiguity and concurrent claimers.

## Success Criteria

- [ ] Concurrent worker/deploy overlap cannot actively send the same lifecycle email key twice.
- [ ] Completed/suppressed first pages cannot starve later lifecycle recipients.
- [ ] Retrying an ambiguous lifecycle send reuses the identical Resend idempotency key.
- [ ] A committed affiliate claim is invisible to other claimers until completion or lease expiry.
- [ ] Neither Resend nor affiliate I/O occurs inside an open claim transaction.
- [ ] Existing non-lifecycle email callers and tests remain valid.
- [ ] Disabled email never consumes a delivery key or writes a sent log.
- [ ] Disabled email/affiliate jobs never occupy a worker slot, claim rows, or call providers.

## Risk Assessment

- **Provider accepted request but response was lost:** stable Resend idempotency makes retry safe within provider guarantees; record this contract in tests and runbook.
- **Migration ordering:** chain the mandatory affiliate ownership revision after the runtime and notification-claim revisions, and test every new revision boundary.
- **Poison item blocks queue:** bounded claims, attempt caps, and existing dead-letter behavior allow later rows to progress.

## Security Considerations

Idempotency keys use opaque user IDs, not email addresses. Provider errors are sanitized. Email eligibility, unsubscribe, authentication, and affiliate payload protection remain enforced by existing domain services.

## Next Steps

Phase 4 registers these steps as dormant. Phase 5 cuts over notification only; email or affiliate requires a separate later activation gate.
