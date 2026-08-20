---
title: "Separate Hosted Worker Portability Amendment"
date: 2026-08-08
status: accepted
scope: plan-only
---

# Separate Hosted Worker Portability Amendment

## Summary

The initial rollout remains one background process on the current Render Standard web instance. The implementation must also make a later move to a separately hosted background-worker service a deployment/configuration change, not a worker rewrite.

## Decisions

- Keep one image and one worker command: `python -m src.background_worker`.
- Treat `docker-entrypoint.sh` as a colocated deployment adapter only.
- Make worker startup, SIGTERM, exit status, database engine, provider resources, heartbeat, and cleanup independent of FastAPI/Uvicorn.
- Store coordination, fencing, progress, and health in PostgreSQL only. Do not require localhost IPC, process memory, or persistent container files.
- Add `BACKGROUND_WORKER_HOSTING_MODE=colocated|dedicated`; current default and rollout value are `colocated`.
- Give the worker its own optional database URL/mode and pool settings, with safe fallbacks to the current app runtime connection values.
- Build worker engines/sessions/UoWs through a side-effect-free explicit-settings factory; keep API globals as wrappers and inject worker factories into every workload.
- Use an opaque per-process instance ID and hosting mode in durable health; do not expose lease tokens or sensitive host metadata.
- Persist one bounded, owner/epoch-fenced health snapshot so cross-service API health includes freshness, outcomes/lag, resource samples, pauses, and degradation across takeover.
- Read the current container's cgroup limits in both modes. Keep API p95 as an external colocated-mode rollout gate.

## Current Scope

Included now: the portability seam, standalone process tests, same-image smoke tests, durable cross-mode takeover tests, and future migration/rollback instructions.

Excluded now: provisioning, paying for, deploying, or cutting over a separate hosted worker; autoscaling; multiple active executors; a new broker or job framework.

## Future Migration Contract

1. Create the separate worker from the same image/commit and run `python -m src.background_worker`.
2. Supply worker/provider/database environment values and set hosting mode to `dedicated`.
3. Start with shadow mode and all workload flags false as a standby.
4. Pass the provider connection-budget gate. Direct mode uses configured API pool capacity; `NullPool` uses at least 150% of the measured representative API client-connection peak with a floor of 10 per overlapping instance, never the policy's zero pool capacity. Add two permits per old/new worker process and a reserve of at least 10 or 20% of the provider limit.
5. Deploy the web service with its colocated worker disabled; its old worker drains/releases on SIGTERM and Uvicorn follows normal deploy restart.
6. Verify the protected API health route transitions from the stale old snapshot to a fresh dedicated instance, then deploy notification execution there. Shared lease epochs and row ownership fence accidental process overlap.
7. Roll back with the same restart-based disable, drain/verify, then enable ordering. Keep the same schema, durable progress, queue rows, and image.

## Validation

- Standalone import/start does not initialize FastAPI or Uvicorn.
- Standalone startup creates exactly one explicitly configured worker engine and every workload uses its injected gated session/UoW factory.
- Standalone SIGTERM closes both in-flight batches, heartbeat, providers, and worker engine within the grace deadline.
- Colocated and dedicated-mode contenders sharing PostgreSQL have one valid lease owner and reject stale completion.
- The API observes worker health from durable state even when no worker process is local.
- One Docker image supports both the web entrypoint and standalone worker command.
- The image health check does not require a local API port in dedicated mode.
- Dedicated image liveness does not open a third database connection; heartbeat freshness is checked through the protected API health route.
- CPU utilization uses cgroup usage deltas normalized by quota/period over monotonic elapsed time; invalid/first/reset/unlimited samples fail closed.
- Two DB permits are per worker process; topology overlap is separately checked against the aggregate provider connection limit.
- Budget tests cover direct and `NullPool` modes; missing pooler telemetry/limits or a zero derived API contribution block rollout.
- A topology handoff changes no schema, queue format, or workload implementation.

## Verified Platform Assumption

Render documents Background Workers as continuous services without incoming network traffic, so detailed health remains exposed by the separate API through shared PostgreSQL. Render also supports a custom Docker Command per service instead of the Dockerfile `CMD`, allowing the same image to run `python -m src.background_worker`.

- https://render.com/docs/background-workers
- https://render.com/docs/docker

## Unresolved Questions

None. The future hosting vendor/service size is intentionally deferred until migration is requested.
