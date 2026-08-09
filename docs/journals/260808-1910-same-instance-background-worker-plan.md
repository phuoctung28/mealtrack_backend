# 260808 Same Instance Background Worker Plan

Planning entry for the portable worker docs-only PR.

## Current State

- No application code changes.
- Plan artifacts only.

## Evidence Targets

- `alembic heads` should remain `20260807000002 (head)`.
- `lint-imports` should remain `4 kept/0 broken`.
- `ck plan status` should show valid `5 pending phases`.
- Whitespace and merge-marker checks should pass.
- `git diff --check` should pass.

## Rollout Notes

- Same Render instance first.
- Notification-only activation.
- Max two bounded batches.
- Email and affiliate dormant.
- Same image and standalone command support later separate hosting via config-only migration.
