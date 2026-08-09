# Same Instance Background Worker Brainstorm

## Decision Summary

- Start on the same Render instance as the existing app.
- Activate notification-only behavior first.
- Cap each run at a maximum of two bounded batches.
- Keep email and affiliate paths dormant until a later plan.
- Reuse the same image and standalone command so separate hosting later is a config-only migration, not a redesign.

## Notes

- The first rollout should minimize operational change.
- The worker should be easy to reason about during partial rollout.
- Portability matters more than early optimization.
