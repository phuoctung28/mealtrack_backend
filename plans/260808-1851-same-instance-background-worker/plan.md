---
title: "Same-Instance Background Worker"
description: "Replace the active notification cron with a portable two-slot worker, colocated first and separately hostable later."
status: pending
priority: P1
effort: "8-12 engineering days plus staged observation"
branch: "main"
tags: [backend, infrastructure, database, reliability]
blockedBy: []
blocks: []
created: "2026-08-08T11:55:21.869Z"
createdBy: "ck:plan"
source: skill
---

# Same-Instance Background Worker

## Overview

Run the standalone background-worker executable beside the single Uvicorn process on the existing Render Standard instance. It executes at most two different bounded job batches concurrently: notification dispatch in the urgent lane and one maintenance task in the second lane. PostgreSQL stores coordination and progress; email/affiliate remain disabled for the initial notification-only rollout.

## Scope Decision

**AMENDED — implement all adapters, activate notification only, preserve hosting portability.** Existing cron entrypoints, repositories, queues, and observability are reused. The worker has a hard concurrency cap of two and never runs two batches of the same job type. A standalone executable, worker-owned lifecycle, worker-specific DB settings, and PostgreSQL-only coordination are included. Provisioning a separate hosted service, autoscaling, a general-purpose job framework, and new infrastructure remain excluded.

## Architecture

```text
same image + standalone command: python -m src.background_worker
├── now: docker-entrypoint.sh supervises it beside Uvicorn
└── later: a separate hosted worker runs the command directly
      ├── coordination: PostgreSQL lease/heartbeat
      ├── urgent slot: push dispatch
      ├── maintenance slot: precompute OR trial OR cleanup
      └── email/affiliate registered but disabled initially
```

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Durable Runtime Foundation](./phase-01-durable-runtime-foundation.md) | Pending |
| 2 | [Bound Notification Workloads](./phase-02-bound-notification-workloads.md) | Pending |
| 3 | [Harden Email and Affiliate Delivery](./phase-03-harden-email-and-affiliate-delivery.md) | Pending |
| 4 | [Portable Worker and Colocated Supervision](./phase-04-sibling-worker-and-process-supervision.md) | Pending |
| 5 | [Verification and Staged Cron Cutover](./phase-05-verification-and-staged-cron-cutover.md) | Pending |

## Dependencies

- Approved design: [brainstorm report](../reports/260808-1848-same-instance-background-worker-brainstorm.md)
- Runtime/process research: [researcher 01](./research/researcher-01-worker-coordination-and-process-lifecycle.md)
- Batching/rollout research: [researcher 02](./research/researcher-02-batching-delivery-and-rollout.md)
- User-approved amendment: [bounded concurrency and notification-first rollout](./reports/bounded-concurrency-notification-first-amendment.md)
- Portability amendment: [separate hosted worker migration seam](./reports/separate-hosted-worker-portability-amendment.md)
- Current Alembic head `20260807000002`; Render dashboard access is required only during Phase 5 cutover.

## Success Gates

- Replace the active push cron without a second paid instance; dormant email/affiliate flags remain false until separately activated.
- Run at most two different notification batches concurrently and never overlap two batches of the same job type.
- Survive restarts/deploy overlap through PostgreSQL coordination and at-least-once execution.
- CPU remains below 85%; memory below 75% normally and 85% at peak; web p95 latency regression at or below 20%.
- Push starts within 2 minutes; dormant affiliate/email SLAs apply only during their later activation gates.
- Rollback requires disabling the matching workload flag and re-enabling its Render cron, with no schema rollback.
- A later move to a separately hosted worker uses the same image, command, database state, and workload code; only service topology/config changes.

## Validation Strategy

Focused unit tests, PostgreSQL concurrency/integration tests, migration round-trip, entrypoint supervision tests, Docker smoke tests, cross-topology handoff tests, and staged Render observation across a midnight window. Local tests prove logic; only staging telemetry can prove shared-instance resource and latency gates.

## Hard-Mode Review

Four adversarial reviews plus focused concurrency and portability reviews produced resolved correction clusters. The later user amendments supersede serial execution and affiliate/email-first rollout; see [adjudication](./reports/red-team-adjudication.md) and [portability review](./reports/separate-worker-portability-review.md). Static validation is recorded in [validation report](./reports/plan-validation.md); runtime/resource claims remain Phase 5 gates.

## Unresolved Questions

None. The approved capacity, process, durability, and delivery choices are encoded in the phases.
