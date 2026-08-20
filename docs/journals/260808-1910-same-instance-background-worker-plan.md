---
title: Same-Instance Background Worker Planning Record
date: 2026-08-08 19:10
status: planning-complete
component: background worker / cron replacement
---

# Same-Instance Background Worker Planning Record

## What Happened

The user amended the earlier planning shape. The worker is now bounded to two total job batches: notification dispatch in the urgent lane and one mutually exclusive maintenance lane for precompute, trial scheduling, or cleanup. Initial rollout is notification-only. Email and affiliate remain registered but dormant.

## The Brutal Truth

The hard part is that the first-pass concurrency story was incomplete. “Two slots” sounded clean until the review forced us to admit the heartbeat path could still starve if DB access was not reserved and ordered. The amendment fixed that by making coordination capacity part of the design instead of hoping the worker would stay polite under load.

## Technical Details

The amendment locks in two worker DB permits total, with one ordinary-workload permit and one coordination/heartbeat permit. Slot two only admits when both CPU and memory are below 70%; otherwise concurrency falls back to one or zero. The scheduler may never run two batches of the same job type at once. Focused amendment review found a heartbeat starvation hole, and adjudication resolved it by requiring ordered permit acquisition and reserved coordination capacity. Validation kept the initial rollout notification-only and left email/affiliate execution flags false.

The portability amendment then made the worker future-hosting-safe without provisioning a second service now. Initial deployment stays colocated on the existing Render web instance, but the same image and standalone `python -m src.background_worker` command can later run dedicated hosting. The worker owns DB/provider/signal lifecycle through an explicit-settings session/UoW factory. Coordination, progress, and durable health stay in PostgreSQL only, with a bounded sanitized health snapshot and `colocated|dedicated` mode recorded in the lease state. Dedicated-mode liveness is topology-aware and does not depend on HTTP. Render config changes are restart/deploy operations, not live reloads. Two DB permits are per worker process, with direct and `NullPool` overlap budgeted separately, and cgroup CPU admission uses quota-normalized deltas instead of raw usage counters.

## What We Tried

The amendment review tried to accept the two-slot model as-is and failed. That was useful: it proved the design needed an explicit access contract for heartbeat and claims, not just a generic “bounded concurrency” label. The final shape keeps the notification-first rollout and dormant workloads, but only after the permit order was made explicit.

## Root Cause Analysis

The root cause was under-specifying shared-resource contention. We had workload limits but not a real contract for the coordination path, so a shallow implementation could have deadlocked or starved renewal while still looking “bounded.” The amendment fixed the missing DB-access guarantee.

## Lessons Learned

Bounded concurrency is meaningless unless the heartbeat path has first-class capacity. Also, rollout scope is not a side note: email and affiliate staying dormant is part of the approved initial state, not a future cleanup task.

## Next Steps

Implementation is still pending. The handoff is to build the notification-first two-slot scheduler with ordered permit acquisition, then prove slot-two admission and heartbeat safety under load. Email and affiliate stay dormant until later activation gates are approved. No separate hosted service is provisioned now; the portability seam is just preserved and verified.
