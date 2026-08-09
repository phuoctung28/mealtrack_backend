# Same Instance Background Worker Plan

Status: planning only
Base branch: `main`

This plan covers a portable notification worker that starts on the same Render instance as the current app and can later move to separate hosting with config-only changes.

## Phases

1. `phase-01-discovery.md` - confirm current queues, triggers, and existing command surface.
2. `phase-02-worker-design.md` - define worker boundaries, startup contract, and failure handling.
3. `phase-03-notification-activation.md` - wire notification-only activation path for the first rollout.
4. `phase-04-batching-and-controls.md` - cap execution to two bounded batches and keep email/affiliate flows dormant.
5. `phase-05-separate-hosting-readiness.md` - document the same image and standalone command path for later migration.

## Constraints

- Do not implement runtime changes in this PR.
- Keep the initial deployment on the same Render instance.
- Preserve a config-only migration path to separate hosting later.

## Success Criteria

- Plan is reviewable without code changes.
- Rollout sequencing is explicit.
- The later hosting split is possible without redesigning the worker.
