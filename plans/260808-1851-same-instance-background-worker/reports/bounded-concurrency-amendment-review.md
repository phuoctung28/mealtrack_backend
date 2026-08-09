# Bounded-Concurrency Amendment Review

## Scope

- Reviewed the approved amendment against `plan.md`, all five phase files, adjudication, validation, the approved brainstorm amendment, and the live database/session, entrypoint, and notification paths.
- Review limited to amendment-induced contracts: two workload batches, urgent-plus-maintenance lanes, two worker DB sessions, serialized lease/claim sections, independent heartbeat, notification-only rollout, and dormant email/affiliate execution.
- Preserved the approved batch ceilings, resource thresholds, maximum concurrency, and rollout scope.

## Overall Assessment

**Not implementation-ready yet.** The lane and rollout decisions are consistent, but the two-session cap does not reserve or prioritize database access for the independent heartbeat and does not define lock/semaphore acquisition order. Under the exact two-lane load introduced by the amendment, renewal can be starved or deadlocked even though workload concurrency and session-count tests pass.

## Critical Pass (Blocking)

### High — The heartbeat has no guaranteed path through the two-session budget

- Amendment evidence: the worker caps sessions at two and serializes lease/claim sections, while the heartbeat runs independently outside workload slots (`reports/bounded-concurrency-notification-first-amendment.md:18-20,34`; `phase-01-durable-runtime-foundation.md:28,67`; `phase-04-sibling-worker-and-process-supervision.md:41,79`).
- Live-code evidence: notification and maintenance paths open many independent `AsyncUnitOfWork` scopes (`src/infra/services/cron_notification_dispatch_service.py:234-248,256-285,303-339,424-495`; `src/infra/services/daily_context_precompute_service.py:463-635`; `src/infra/services/cron_trial_push_service.py:52-83`). The engine/pool has no priority or reserved heartbeat connection (`src/infra/database/config_async.py:90-125`), and each UoW's lock is instance-local rather than process-wide (`src/infra/database/uow_async.py:97-110`).
- Failure mode: dispatch and maintenance can occupy both permits. Heartbeat then waits behind workload DB work; if claim code holds a permit while waiting for the claim lock and heartbeat holds the lock while waiting for a permit, renewal deadlocks. Lease expiry permits takeover, converting ordinary saturation into repeatable stale-owner work and provider duplicate ambiguity.
- Required correction, without changing the approved cap: specify one session gate used by **every** worker DB-opening path; give lease renewal bounded priority/reserved access within the two-permit ceiling; define one lock/permit acquisition order and prohibit waiting on the claim lock while holding an incompatible permit; bound DB acquisition/statement time below the renewal safety margin.
- Required test: with dispatch and maintenance both active, saturate the session gate and contend the claim lock; prove heartbeat renewal stays within deadline, total worker sessions never exceed two, no deadlock/takeover occurs, and both direct-pool and `NullPool` modes use the same gate. Existing generic “two-session/serialized-claim” and heartbeat tests (`phase-04...:85`; `phase-05...:60`) do not state this combined contention case.

## Informational Pass (Non-Blocking After the High Finding Is Fixed)

### Medium — SIGTERM wording still describes one in-flight step

- `phase-04-sibling-worker-and-process-supervision.md:82` says shutdown allows “one bounded step,” while the amended worker can have two in-flight batches and later tests explicitly require a two-batch SIGTERM case (`:85`; `phase-05...:60`).
- Clarify that shutdown stops admission, then independently awaits/checkpoints/releases **both** in-flight batches within the shared grace deadline. Assert the terminal state of both claims, not only process exit.

### Low — One Phase 4 handoff sentence retains multi-cron cutover wording

- `phase-04-sibling-worker-and-process-supervision.md:119` says Phase 5 “disables each matching Render cron in controlled stages.” The approved amendment makes Phase 5 notification-only and removes only the active push cron (`reports/bounded-concurrency-notification-first-amendment.md:22-24,45`; `phase-05-verification-and-staged-cron-cutover.md:21,63-67`).
- Replace that sentence with notification-bundle validation followed by active push-cron cutover. Email/affiliate remain registered but dormant and require later activation gates.
- Historical red-team reports still contain their original serial/affiliate-first premises, but adjudication explicitly supersedes them; they are evidence records, not active implementation contracts.

## Positive Observations

- Active plan requirements consistently cap workload concurrency at two, forbid same-job overlap, and restrict initial notification concurrency to dispatch plus one mutually exclusive maintenance batch.
- Email and affiliate remain false-flagged, produce no claims/provider calls/slot use, and are excluded from initial capacity evidence.
- Batch ceilings and CPU, memory, p95, and lag gates remain unchanged.
- The plan correctly separates workload slots from coordination activity and keeps provider I/O outside claim transactions; the blocking finding is specifically the missing DB-access guarantee for that coordination activity.

## Recommended Actions

1. Add the heartbeat/session-priority, acquisition-order, timeout, and combined-contention contracts and test.
2. Make the two-in-flight shutdown semantics explicit.
3. Replace the single stale multi-cron handoff sentence.
4. Re-run the cross-file amendment validation; only then restore an implementation-ready verdict.

## Unresolved Questions

None. The blocking correction does not require a new product decision or a change to approved limits.

**Status:** DONE_WITH_CONCERNS
**Summary:** Focused amendment review completed. One high concurrency contract gap blocks implementation readiness; two wording/test clarifications are non-blocking once it is fixed.
**Concerns/Blockers:** Heartbeat renewal has no guaranteed/ordered access through the shared two-session gate under two-lane contention.
