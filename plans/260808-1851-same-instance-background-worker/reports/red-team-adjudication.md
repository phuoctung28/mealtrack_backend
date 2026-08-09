# Hard-Mode Red-Team Adjudication

## Decision Rule

Evidence-backed findings were merged when they corrected implementation detail without reversing approved topology, scope, ceilings, thresholds, or business rules. Duplicate findings were clustered. A later direct user amendment now supersedes the original serial-execution and affiliate/email-first rollout decisions.

## Accepted Finding Clusters

| # | Accepted correction | Plan update |
|---|---|---|
| 1 | Replace stale/non-existent paths and symbols; place PostgreSQL tests under CI-discovered `tests/integration/postgres/`. | Phases 1-5 file/test maps corrected. |
| 2 | Add notification row owner, lease epoch, claim timestamps/expiry, owner-checked completion/recovery, and live-claim-safe cleanup. | Phase 2 adds mandatory migration and race tests. |
| 3 | Rehydrate active FCM tokens at dispatch; retain row/token mapping; prevent cross-recipient IDs; handle partial token outcomes per row. | Phase 2 dispatch contract expanded. |
| 4 | Freeze precompute cursor upper bound, handle eligibility mutations behind cursor, and bound/query-test the weekly-budget N+1 path. | Phase 2 pagination/query contract expanded. |
| 5 | Define three default-false cron-granularity flags and treat all four push phases as one cutover/rollback unit. | Phases 1, 2, 4, and 5 corrected; later amendment makes notification the initial cutover. |
| 6 | Make affiliate owner/expiry migration mandatory and keep native outbox state authoritative. | Phase 3 corrected. |
| 7 | Add lifecycle daily scan cursor, preserve seven-day suppression, distinguish disabled/deferred from sent, and propagate the exact key through live `EmailService` methods. | Phase 3 corrected. |
| 8 | Renew leadership independently during I/O; fence claims with monotonic epoch; bound provider/step deadlines and stale completion. | Phases 1 and 4 corrected. |
| 9 | Treat Uvicorn as primary and locally restart only the auxiliary worker with bounded backoff. | Phases 4 and 5 availability gates reconciled. |
| 10 | Allow only coordination/metric writes in shadow; keep public liveness coarse; add a protected worker-health endpoint. | Phase 4 corrected. |
| 11 | Use cgroup v2 container counters with hysteresis and fail closed for new claims when unavailable. | Phase 4 resource guard made executable. |
| 12 | Define cadence, schedule keys, catch-up, completion, and starvation prevention for every workload. | Phase 4 workload schedule table added. |
| 13 | Use generic run rows only for cursor-backed scans; retain native queue state for notification/affiliate drains; bounded-prune terminal scan history after 30 days. | Phases 1, 3, and 4 simplified. |
| 14 | Move scheduler orchestration to application layer and inject a minimal domain workload protocol to preserve import contracts. | Phase 4 corrected. |
| 15 | Test every migration boundary, both DB modes, import contracts, and name the live p95 telemetry query before cutover. | Phases 1 and 5 corrected. |

## Deliberately Not Reversed

- Same Render Standard instance, one sibling process, maximum two different workload batches, no broker or paid worker.
- All three cron services and all four push sub-workloads remain in scope.
- Batch ceilings and CPU/memory/latency thresholds remain unchanged.
- At-least-once FCM semantics retain the approved rare provider-acceptance/response-loss duplicate ambiguity; fencing reduces overlap but cannot make FCM exactly once.
- Initial rollout is notification only because email and affiliate are not currently running; both stay behind false execution flags.

## Post-Review User Amendment

- Two workload slots replace serial execution.
- Dispatch may overlap one maintenance batch; precompute, trial, and cleanup remain mutually exclusive.
- Worker DB/session concurrency is two; ordinary workload DB access is one, preserving a coordination permit, while lease/claim critical sections remain serialized.
- Notification supplies initial capacity evidence. Dormant email/affiliate activation requires separate later gates.

Focused amendment review found and resolved heartbeat starvation: ordinary workload DB access is capped at one within the two-permit worker budget, coordination receives due-time priority, and every path follows one acquisition order with deadlines.

## Separate-Hosting Portability Amendment

The user additionally required an easy future move to a separately hosted background worker. This does not reverse the approved initial topology. The plan now makes the worker module a standalone executable with its own DB/provider lifecycle, PostgreSQL-only coordination/health, one image, and explicit `colocated|dedicated` configuration. The current phase implements and tests this seam but does not provision or cut over a separate service.

The focused portability review found five new implementation gaps that the earlier topology review did not test: import-time API DB globals, missing durable health fields, startup-cached Render flags, per-process rather than aggregate DB permits, and undefined cgroup CPU math. The plan now requires an explicit-settings engine/session/UoW factory, bounded fenced health snapshot, restart-based rollback/handoff, provider-level overlap budgeting, and quota-normalized CPU delta sampling. A recheck exposed `NullPool.total_capacity=0`; the final pooler formula instead uses a representative measured API client-connection peak with 50% headroom, floor 10 per overlapping instance, a 20%/10-connection reserve, and fail-closed telemetry/limit gates.

## Remaining Blockers

None in the plan. Whether two slots satisfy the existing resource/latency limits remains an explicit Phase 5 staging gate; configuration can fall back to one slot without architecture change.
