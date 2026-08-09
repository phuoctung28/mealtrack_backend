---
title: "Same-Instance Background Worker Brainstorm"
date: 2026-08-08
status: approved
scope: architecture
---

# Same-Instance Background Worker Brainstorm

## Problem

The current cron-based notification work can exceed memory around midnight, when daily precomputation and delivery work concentrate into one execution window. The backend already runs on a Render Standard instance with roughly 20% baseline CPU and memory utilization, so the first goal is to reuse that capacity safely instead of immediately adding another paid service.

## Confirmed Constraints

- Initial hosting stays on the current backend instance.
- Run a second worker process beside one Uvicorn process.
- Handle multiple job batches, but cap concurrency at two.
- CPU must remain below 85%.
- Memory should remain below 75% normally and 85% at peak.
- Notification is the only currently active cron workload.
- Email and affiliate support may be prepared, but both remain disabled until separately activated.
- Keep the design minimal and avoid a broker or general-purpose job framework.
- Preserve a simple later migration to a separately hosted worker.

## Options Considered

### 1. Keep Render cron and only reduce batch size

Smallest code change, but it retains concentrated schedules, weak restart continuity, deploy overlap ambiguity, and separate cron operational state. It does not provide steady backpressure against midnight spikes.

### 2. Run work inside the FastAPI request process

No second process, but job failures, blocking SDK calls, database pressure, and event-loop contention would directly affect web serving. Process restarts would also lose in-memory scheduler state.

### 3. Run a sibling worker on the current instance

Recommended. A standalone process can poll small durable batches continuously, share the current instance initially, and reduce admission when the container is under pressure. PostgreSQL already exists and can provide leases, fencing, cursors, and progress without adding Redis or another queue service.

### 4. Provision a separate hosted worker immediately

Operationally isolated, but it adds cost and infrastructure before the workload is measured. The implementation should preserve this future topology without provisioning it now.

## Decision

Use one standalone background-worker executable. Initially supervise it beside a single Uvicorn process in the existing Render web container. Coordinate through PostgreSQL, execute bounded batches with a hard concurrency cap of two, and activate only the complete notification workload bundle.

Decision: approved.

## Approved Architecture

```text
Render Standard instance
|
+-- container supervisor
    +-- Uvicorn: FastAPI request serving
    +-- job worker: at most two different bounded batches
        +-- PostgreSQL leader lease and run progress
        +-- urgent lane: notification dispatch
        +-- maintenance lane: precompute, trial, or cleanup
        +-- dormant flags: lifecycle email and affiliate outbox
```

### Coordination

- Use a PostgreSQL lease or advisory lock to elect one active worker during overlapping deploys or future scaling.
- Persist scheduled-run identity, cursor, attempts, lease expiry, completion, and last error.
- Derive stable run keys from job and schedule, such as timezone plus local date.
- Release or expire claims safely after process death.
- Handle `SIGTERM`; stop claiming new batches, finish or release the active batch, then exit.

### Backpressure

- Global workload concurrency: two; one batch per job type.
- Serialize claim/lease critical sections; allow committed workload/provider activity to overlap.
- Configurable batch sizes and pauses; tune through environment values after production observation.
- Process urgent due notifications before lower-priority cleanup.
- Never retain complete run datasets in memory.
- Measure Render CPU, memory, and API latency throughout staged rollout.

### Initial Batch Ceilings

| Workload | Initial ceiling | Cadence target |
|---|---:|---|
| Notification precompute | 100 users | Continue from durable keyset cursor |
| Notification dispatch | 100 rows | Poll frequently; normal delay at most 2 minutes |
| Trial push scheduling | 100 subscriptions | Every 2 minutes |
| Lifecycle email | 25 recipients | Start within 15 minutes of 09:00 UTC |
| Affiliate outbox | 50 rows | Normal delay at most 5 minutes |
| Expired-row cleanup | 500 rows | Daily, repeated until empty |

Batch sizes are safe starting hypotheses, not verified production constants. Validate and tune them against Render metrics.

## Delivery Semantics

- Use at-least-once processing with idempotent side effects.
- Keep the notification unique constraint for row-level deduplication.
- Use stable Resend idempotency keys for lifecycle email retries.
- Preserve downstream affiliate event IDs and make database claiming exclusive.
- Accept that FCM cannot provide absolute exactly-once delivery: a crash after provider acceptance but before the database success write can produce a rare duplicate. Prefer this over silently losing a notification.

## Rollout

1. Add durable worker coordination and bounded processing while existing cron remains enabled.
2. Validate batch behavior with focused tests and a production-like dataset.
3. Deploy worker disabled; record web-only CPU, memory, and latency baseline.
4. Enable all four notification steps and validate dispatch-plus-maintenance concurrency.
5. Disable the active push cron only after the complete notification bundle is healthy.
6. Observe at least one timezone-midnight precompute window before deleting the push cron service.
7. Keep email and affiliate execution flags false; activate either later only through its own observed rollout.
8. Keep feature flags that disable worker claims for emergency rollback.

## Success Criteria

- The active push cron can be removed after monitored notification cutover; dormant email/affiliate execution stays disabled.
- Render CPU stays below 85% during job execution.
- Memory stays below 75% normally and below 85% during peaks.
- API p95 latency rises no more than 20% while jobs run.
- Normal push delay is at most 2 minutes.
- Normal affiliate delay is at most 5 minutes.
- Lifecycle email begins within 15 minutes of its daily target.
- Interrupted work resumes without lost database jobs.
- No new queue framework or separately billed Render service is required.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Shared CPU harms API latency | Maximum two different batches, dynamic admission, pauses, small ceilings, staged tuning |
| Shared RAM causes another OOM | Keyset pagination, bounded claims, bounded inserts, peak-memory monitoring |
| Duplicate workers during deploy | PostgreSQL leadership and expiring leases |
| Worker dies silently | Supervisor restart with backoff plus health/last-success reporting |
| Partial timezone precompute marked complete | Explicit durable cursor and completion record; remove current any-row sentinel |
| Email duplicate after retry | Stable Resend idempotency key plus database run identity |
| FCM ambiguous success on crash | At-least-once policy, stable notification identifiers, stale-claim recovery |
| Rollout regresses delivery | Per-job feature flags and cron-to-worker staged cutover |

## Dependencies

- Existing PostgreSQL database and async SQLAlchemy runtime.
- Existing notification queue, email log, and affiliate outbox models.
- Render Standard instance metrics during staged rollout.
- Resend idempotency-key support.

## References

- `src/cron/push.py`
- `src/cron/email.py`
- `src/cron/affiliate_outbox.py`
- `src/infra/services/daily_context_precompute_service.py`
- `src/infra/services/cron_notification_dispatch_service.py`
- `src/infra/services/cron_lifecycle_email_service.py`
- `src/infra/services/affiliate_outbox_dispatch_service.py`
- `src/infra/event_bus/background_task_manager.py`
- Render instance types: https://render.com/docs/compute-plans
- Render service metrics: https://render.com/docs/service-metrics
- Render deploy lifecycle: https://render.com/docs/deploys
- Resend idempotency keys: https://resend.com/docs/dashboard/emails/idempotency-keys

## Next Steps

- Create an implementation plan from this approved report.
- Prefer tests-first planning because the change replaces production scheduling and delivery behavior.

## Portability Amendment

The first deployment remains a sibling process on the current Standard web instance. The worker must nevertheless be a standalone command with worker-owned database/provider lifecycle and PostgreSQL-only coordination. The same image and `python -m src.background_worker` command must later run on a separately hosted worker through environment/service changes only; provisioning that service is outside the current scope.

## Unresolved Questions

None.
