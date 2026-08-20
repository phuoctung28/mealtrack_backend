---
title: "Bounded Concurrency and Notification-First Amendment"
type: plan-amendment
status: approved
date: 2026-08-08
---

# Bounded Concurrency and Notification-First Amendment

## Summary

The user clarified that lifecycle email and affiliate delivery are not currently running, and explicitly replaced serial workload execution with bounded concurrency. This amendment supersedes only the old concurrency and rollout-order decisions; the same-instance sibling process, PostgreSQL durability, workload scope, batch ceilings, and resource gates remain approved.

## Decisions

| Area | Amended decision |
|---|---|
| Worker concurrency | Maximum two workload batches at once; never two batches of the same job type |
| Initial notification lanes | Urgent lane: push dispatch. Maintenance lane: one of precompute, trial scheduling, or cleanup |
| Database use | Two total worker DB permits; at most one ordinary workload DB section, leaving one permit available for heartbeat/coordination; claims serialized and committed before overlap |
| Resource admission | Slot two starts only below 70% CPU and memory; concurrency reduces to 1 or 0 under pressure; hard gates unchanged |
| Initial rollout | Notification bundle only, because it is the only active workload |
| Email/affiliate | Implemented as planned but execution flags remain false; excluded from initial capacity evidence and cron cutover |
| Later activation | Each dormant workload requires its own baseline, observation, and rollback gate before enablement |

## Notification Execution Shape

```text
max_concurrency = 2

slot A (latency):    push dispatch
slot B (maintenance): precompute OR trial scheduling OR cleanup

coordination heartbeat runs independently and does not consume a workload slot
```

The scheduler may leave a slot empty. It does not fill both slots merely because work exists; cgroup pressure and web latency protection remain admission gates.

## Required Plan Changes

- Replace every serial-loop/one-batch statement with bounded concurrency two.
- Add two total DB permits, a one-permit ordinary-workload gate, heartbeat-priority coordination, and a fixed acquisition order.
- Add tests for dispatch plus maintenance overlap, same-job exclusion, DB connection caps, lease loss, shutdown, and resource-driven 2 -> 1 -> 0 admission.
- Make Phase 5 notification-first and keep email/affiliate execution flags false.
- Change initial success from removing all three cron services to replacing the active push cron; later dormant activation remains covered but is not part of initial capacity proof.

## Unresolved Questions

None. The user directly approved this amendment.
