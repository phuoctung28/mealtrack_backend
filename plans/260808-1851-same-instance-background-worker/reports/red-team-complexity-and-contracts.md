# Red-Team Complexity and Contract Review

## Scope

- Read `plan.md`, all five phase files, both research reports, the approved brainstorm, and the three earlier red-team reports.
- Verified live notification/FCM, lifecycle-email/Resend, affiliate-outbox, database-pool, migration, health, test-discovery, and import-layer contracts.
- Lenses: Scope & Complexity Critic + Contract Verifier. Previously reported cutover order, per-workload flags, row ownership, lease fencing, resource scope, health auth, stale recipient tokens, and worker-crash availability are not repeated.
- Two-pass result: **6 blocking findings, 4 informational findings**.
- Verdict: **not implementation-ready**. The approved same-instance sibling process, serial execution, all cron workloads, no broker, thresholds, and batch defaults remain viable and unchanged.

## Pass 1 — Blocking Findings

### F1 — Critical — FCM batching cannot preserve per-row outcomes and leaks grouped row IDs across recipients

- **Plan location:** `phase-02-bound-notification-workloads.md:35,66,86` promises existing idempotency plus preserved per-message results and partial-failure behavior.
- **Code/doc evidence:** The dispatcher groups unrelated users by `(notification_type, title, body)` and stores tokens and row IDs in separate flat arrays (`src/infra/services/cron_notification_dispatch_service.py:97-100,126-129,176-179`). It then puts every grouped row ID into one shared FCM data payload (`src/infra/services/cron_notification_dispatch_service.py:185-205`). Firebase returns failures by token position while still returning top-level `success=True` for partial failure (`src/infra/services/firebase_service.py:173-203`). The dispatcher only deactivates failed tokens and marks *all* grouped rows sent whenever no wholesale call failed (`src/infra/services/cron_notification_dispatch_service.py:207-214`).
- **Contract/scope consequence:** After batching, there is no row-to-token mapping. If user A's only token fails while user B's succeeds, A's row is durably marked sent even though nothing reached A. Every token also receives opaque notification IDs belonging to other users. The plan cannot honestly claim per-message preservation or at-least-once row delivery while retaining this grouping shape.
- **Smallest correction:** Carry `(row_id, token)` through each 500-token chunk and aggregate results per row. Mark a row sent only when at least one current token succeeds; retry/fail it when all tokens fail according to error class. Remove multi-user `notification_ids` from the shared payload, or group provider calls at the recipient/row boundary if mobile requires that field. Add a mixed-success two-user contract test.

### F2 — High — Lifecycle-email batching has recipient claims but no scan cursor, so the first page can starve every later recipient

- **Plan location:** `phase-03-harden-email-and-affiliate-delivery.md:38-40,64-65`; `phase-04-sibling-worker-and-process-supervision.md:62`.
- **Code/doc evidence:** Phase 3 describes one durable claim per recipient but no aggregate email-scan run/cursor. Current candidate queries have neither `ORDER BY`, cursor, nor limit (`src/infra/services/cron_lifecycle_email_service.py:53-72,74-94`). Inactive users remain eligible on later reads, and recent/completed recipients are skipped only after selection (`src/infra/services/cron_lifecycle_email_service.py:34-46,96-110`).
- **Contract/scope consequence:** A straightforward `.limit(25)` implementation repeatedly returns the same first 25 eligible users. Their per-recipient keys are then skipped as completed/owned, but recipient 26 is never selected. The worker may report an empty batch/completion while most recipients are unsent, violating the 25-recipient step and 09:00 start/completion flow.
- **Smallest correction:** Define one daily scan run per lifecycle type with a durable keyset cursor and deterministic ordering, separate from each recipient delivery claim. Checkpoint the cursor for every examined row, including suppressed/owned rows, and mark the scan complete only after the final page. Test more than two pages where page one is already completed.

### F3 — High — `EMAIL_ENABLED=false` is reported as delivery success and would permanently complete claimed work

- **Plan location:** `phase-03-harden-email-and-affiliate-delivery.md:63-65,81-85`; `phase-05-verification-and-staged-cron-cutover.md:62,65`.
- **Code/doc evidence:** `ResendEmailAdapter` returns `EmailResult(success=True, message_id="disabled")` without calling Resend when email is disabled (`src/infra/adapters/resend_email_adapter.py:34-36`), and the unit test locks in that contract (`tests/unit/infra/adapters/test_resend_email_adapter.py:40-55`). Current lifecycle code treats any `success=True` as sent and writes `EmailLog(status="sent")` (`src/infra/services/cron_lifecycle_email_service.py:112-145`). Phase 3 says a successful provider result completes the owned run.
- **Contract/scope consequence:** A staging/production flag mistake, or enabling worker execution before provider delivery, consumes deterministic recipient keys and records emails as sent although no provider call occurred. Re-enabling email later will not replay them; rollout evidence and recipient counts become false.
- **Smallest correction:** Make the provider result distinguish `sent`, `disabled/skipped`, and `failed`. Only `sent` may complete the recipient claim and create a sent email log; disabled work must remain deferred/unclaimed. Preserve existing non-lifecycle behavior explicitly and test worker-enabled/email-disabled recovery.

### F4 — High — The stable Resend key has no defined path through the actual lifecycle service API

- **Plan location:** `phase-03-harden-email-and-affiliate-delivery.md:27,36,49-52,63-65`.
- **Code/doc evidence:** The low-level port is `EmailServicePort.send_email(to, subject, html_body, tags)` (`src/domain/ports/email_service_port.py:16-27`). Lifecycle orchestration does not call that port directly; it calls `EmailService.send_reengagement_email(...)` and `send_trial_expiring_email(...)` (`src/infra/services/cron_lifecycle_email_service.py:112-129`). Those two public methods accept no idempotency argument and invoke the adapter without one (`src/domain/services/email_service.py:59-81,83-107`). Phase 3 explicitly names the wrong port path and only generically says to discover lifecycle files.
- **Contract/scope consequence:** Adding an optional argument to the port and Resend adapter can compile while the deterministic key never reaches the provider. Database claim tests would pass, but response-loss retries would be sent without provider idempotency, breaking the plan's strongest email guarantee.
- **Smallest correction:** Name the exact live contract and add a keyword-only idempotency argument to only the two lifecycle `EmailService` methods, forwarding it unchanged to `EmailServicePort.send_email`. Keep welcome, cancellation, and web-funnel callers unchanged. Add a test that starts with the recipient run key and asserts the adapter receives that exact key on first attempt and retry.

### F5 — High — Workload recurrence, schedule keys, and missed-run policy are undefined

- **Plan location:** `plan.md:58-62`; `phase-01-durable-runtime-foundation.md:34,63`; `phase-04-sibling-worker-and-process-supervision.md:62-63,69`.
- **Code/doc evidence:** Existing executor cadence is part of the current contract: push every two minutes (`src/cron/push.py:4-11`), lifecycle email daily at 09:00 UTC (`src/cron/email.py:4-10`), and affiliate every five minutes (`src/cron/affiliate_outbox.py:4-7`). Phase 1 adds poll/yield settings but no workload schedules. Phase 4 says only "calculate due work" and test due-time calculation without specifying trigger, schedule key, allowed window, or catch-up behavior.
- **Contract/scope consequence:** Implementers must invent whether a late 09:00 email run is caught up or skipped, when timezone precompute becomes due, whether cleanup is daily, and how often queue drains receive new run keys. The stated 2/5/15-minute SLAs and deterministic-run guarantees cannot be verified against an absent schedule contract.
- **Smallest correction:** Add one compact workload table defining: due predicate/cadence, schedule-key format, catch-up window, completion condition, and next eligibility for precompute, trial scheduling, dispatch, cleanup, lifecycle email, and affiliate delivery. Preserve the current 2-minute, 5-minute, 09:00 UTC, timezone-date, and daily-cleanup behavior unless the approved design says otherwise.

### F6 — High — The generic job-run abstraction duplicates queue-native state and has no valid “completed” meaning for continuous drains

- **Plan location:** `phase-01-durable-runtime-foundation.md:22,34,40,60`; `phase-03-harden-email-and-affiliate-delivery.md:40`; `phase-04-sibling-worker-and-process-supervision.md:62-63`.
- **Code/doc evidence:** Notifications already own deterministic row identity, due time, status, and dedupe in `notifications` (`src/infra/database/models/notification/notification.py:22-59`). Affiliate rows already own unique event identity, status, attempts, and next-attempt time (`src/infra/database/models/affiliate_event_outbox.py:17-35`). The affiliate dispatcher already returns a bounded summary after native queue claims (`src/infra/services/affiliate_outbox_dispatch_service.py:16-35,77-89`). The plan nevertheless gives every logical run another durable status/claim/cursor and says affiliate gets an aggregate scheduler run.
- **Contract/scope consequence:** Dispatch and affiliate are continuously due whenever new native queue rows arrive; a scheduler run marked `completed` can suppress later arrivals, while minute/poll-specific run keys create unbounded duplicate coordination rows. Two durable state machines also make rollback authority ambiguous: native queue status says work is due while the aggregate run says completed or failed.
- **Smallest correction:** Use `background_job_runs` only for cursor-based scheduled scans (precompute, lifecycle candidate scans, trial scan, cleanup). Let notification and affiliate drains use their native due rows plus the single leader lease; persist metrics, not a second completion state. Document this classification in the workload table from F5.

## Pass 2 — Informational Findings

### F7 — Medium — The migration round-trip command only exercises the last of at least two planned revisions

- **Plan location:** `phase-01-durable-runtime-foundation.md:46,65,73`; `phase-03-harden-email-and-affiliate-delivery.md:54-67`; `phase-05-verification-and-staged-cron-cutover.md:58-60,72-83`.
- **Code/doc evidence:** Phase 1 fixes a runtime-state revision after `20260807000002`; Phase 3 requires a later affiliate-ownership schema revision because the live model has no owner/lease fields (`src/infra/database/models/affiliate_event_outbox.py:26-31`). Phase 5 instructs only upgrade head, downgrade one revision, upgrade again. Repository standards require new migrations to chain as one head (`docs/standards/db-api.md:66-75`).
- **Contract/scope consequence:** At final head, `downgrade -1` tests only the affiliate revision. The Phase 1 runtime migration's downgrade/upgrade can be broken while the success criterion still reports a migration round trip.
- **Smallest correction:** Test each new revision boundary explicitly, or downgrade the disposable database to `20260807000002` and upgrade back to head, asserting both revisions' objects at each boundary. Keep operational rollback schema-free as already approved.

### F8 — Medium — Scheduler orchestration is assigned to Infrastructure, where the enforced import graph cannot use app/CQRS use cases

- **Plan location:** `phase-04-sibling-worker-and-process-supervision.md:45-49,62`; Phase 2/3 workload registration and dependency-wiring references.
- **Code/doc evidence:** The architecture assigns orchestration to Application and external adapters/repositories to Infrastructure (`docs/system-architecture.md:28-48,54-60`; `docs/cqrs-guide.md:9-21`). CI's import contract forbids `src.infra` from importing `src.app` (`.importlinter:146-160`), and a fresh `lint-imports` run keeps all four contracts. The proposed scheduler is `src/infra/services/background_job_worker_service.py`. Affiliate delivery has no domain delivery port at all: `AffiliateServicePort` defines only `validate_code` (`src/domain/ports/affiliate_service_port.py:15-18`), while the dispatcher constructs `AffiliateServiceAdapter` directly (`src/infra/services/affiliate_outbox_dispatch_service.py:6-25`).
- **Contract/scope consequence:** Following the file map either creates a new infra-to-app import that fails CI, or cements all job orchestration and provider construction in Infrastructure, bypassing the project's composition/CQRS boundary. This also makes provider fakes and worker contract tests harder than the plan implies.
- **Smallest correction:** Put the serial scheduler/use-case service under `src/app/services/` and inject minimal workload/delivery ports from the root `src.background_worker` composition module. Add only the missing affiliate-delivery and push-delivery protocols needed by this worker; do not create a command/event class per polling tick.

### F9 — Medium — A 25-recipient email cap still leaves repeated scans and an N+1 suppression query

- **Plan location:** `phase-03-harden-email-and-affiliate-delivery.md:32,64,69`; `phase-05-verification-and-staged-cron-cutover.md:63-65` shared-resource gates.
- **Code/doc evidence:** Current code executes `_has_recent_email` once per candidate (`src/infra/services/cron_lifecycle_email_service.py:34-46`), and every check opens a UoW and performs a separate query (`src/infra/services/cron_lifecycle_email_service.py:96-110`). `email_logs` has `(user_id, email_type)` and `sent_at` as separate indexes, not the actual three-column filter order (`src/infra/database/models/email_log.py:28-30`). Candidate filters use `users.last_accessed` and subscription status/date (`src/infra/services/cron_lifecycle_email_service.py:58-91`), while live indexes do not match those compound page predicates (`src/infra/database/models/user/user.py:56-62`; `src/infra/database/models/subscription.py:58-63`). Database standards require query-shaped indexes backed by `EXPLAIN` evidence (`docs/standards/db-api.md:95-102`).
- **Contract/scope consequence:** Limiting returned recipients bounds provider calls, not database work. Every page can add 25 suppression queries and repeatedly scan/sort sparse eligibility sets, competing with the API on the same CPU/database budget.
- **Smallest correction:** Batch-load recent-email suppression for the selected user IDs in one query. Define the final keyset query first, run `EXPLAIN`, and add only the compound/partial indexes its filter and order require. Add a query-count assertion for a full 25-recipient page.

### F10 — Medium — Job-run retention is promised in Phase 1 but explicitly deferred beyond completion

- **Plan location:** `phase-01-durable-runtime-foundation.md:34,60,87`; `phase-03-harden-email-and-affiliate-delivery.md:40,64`; `phase-05-verification-and-staged-cron-cutover.md:67,102`.
- **Code/doc evidence:** Phase 1 says Phase 5 will define pruning. Phase 5 contains no retention setting, index, bounded prune operation, test, or todo; it instead opens a future task after verified completion. Phase 3 creates a durable schedule claim for each lifecycle recipient/date, which is much higher cardinality than one row per daily workload.
- **Contract/scope consequence:** The shipped design has append-only recipient and schedule history with no operational bound, contradicting Phase 1's state-growth mitigation. Deferring cleanup also leaves no reviewed answer for which failed/processing records must remain recoverable.
- **Smallest correction:** Define retention semantics before cutover: terminal-only eligibility, a bounded delete limit, and the supporting timestamp/status index. If the retention duration must be measured, make it configurable and initially disable deletion, but include the query, metric, and runbook decision gate now.

## Positive Observations

- The plan correctly avoids a broker/general job framework and reuses queue-native notification and affiliate durability.
- Optional email-port evolution can remain source-compatible if the key is keyword-only and lifecycle-only callers opt in.
- The default unit command and PostgreSQL command documented in `docs/testing-standards.md:61-78` are valid; the remaining test gap is revision coverage, not command syntax.
- The root `src.background_worker` module is a suitable composition boundary because it is outside the enforced app/infra packages.

## Recommended Actions

1. Fix FCM row/token result mapping before treating the existing dispatch service as a reusable bounded workload.
2. Specify lifecycle scan cursor and complete email outcome/idempotency contracts.
3. Add the workload schedule/classification table; keep queue drains native and scheduled scans cursor-backed.
4. Correct scheduler layer placement with the minimum missing provider ports.
5. Expand migration, query-efficiency, and retention verification before staging cutover.

## Behavioral Checklist

- [x] Concurrency: native queue state versus scheduler-run state, lifecycle page progress, and retry result ownership checked.
- [x] Error boundaries: disabled email, partial FCM failure, and provider result propagation checked.
- [x] API/provider contracts: Resend key path, FCM per-token result shape, and affiliate delivery port checked.
- [x] Backwards compatibility: non-lifecycle email callers, cron cadence, and migration chain checked.
- [x] Input/config validation: workload scheduling and retention configuration gaps checked; earlier reports already cover flag/cap validation.
- [x] Auth/authz: no new control endpoint; no additional auth finding beyond earlier protected-health review.
- [x] N+1/query efficiency: lifecycle suppression and candidate index shapes checked.
- [x] Data leaks: cross-recipient FCM row IDs and raw provider-result boundaries checked.
- [x] Fact-checked: all plan paths, live symbols, import contracts, provider call shapes, tests, indexes, and migration claims grep/read-verified.

## Unresolved Questions

- Does the mobile client consume `data.notification_ids`? The backend currently emits a multi-user CSV, so the correction should verify the mobile contract before removing or changing the field.
- What retention duration is operationally required for completed and failed background job runs? This is the only new value not fixed by the approved decisions.

**Status:** DONE_WITH_CONCERNS
**Summary:** Final complexity/contract pass found 6 blocking and 4 informational findings not covered by earlier reviews. The smallest safe design keeps scheduled scans cursor-backed, continuous queues native, and provider outcomes explicitly mapped.
**Concerns/Blockers:** FCM row/result loss, lifecycle scan starvation, false email-success semantics, missing Resend key propagation, and undefined recurrence must be corrected before implementation.
