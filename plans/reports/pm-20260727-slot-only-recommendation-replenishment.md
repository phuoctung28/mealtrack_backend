# Slot-only recommendation replenishment progress

## Status

- Branch: `codex/slot-only-recommendation-replenishment`
- Plan: `in-progress`
- Phase 1: `in-progress`
- Phase 2: `in-progress`
- Phase 3: `pending`

## Delivered

- Added forward migration `20260727000001_add_meal_recommendation_candidate_lifecycle.py`.
- Added backend-owned `seen_at` and `retired_at` candidate lifecycle state.
- Initial selected candidates are persisted as seen; retired rows remain auditable and are omitted from active detail.
- Automatic swaps consume unseen active candidates and replenish only an exhausted slot with five deterministic candidates.
- Added post-lock swap idempotency replay check and internal `stored_candidate` / `replenished_candidate` outcome metrics.
- Preserved `MealRecommendationSlotDetailResponse`; no Flutter source change required by the current response contract.
- Updated mobile handoff and architecture docs.

## Verification

- `2024 passed` in the full unit plus migration suite before the final focused rerun; final focused migration/recommendation slice: `44 passed`.
- Focused mypy passed on changed recommendation modules.
- Focused Ruff passed on changed implementation/test files.
- Alembic heads: `20260727000001 (head)`.
- Full repository Ruff remains pre-existing/noisy (`1,085` findings); not treated as feature evidence.
- Migration status/test scripts remain blocked locally by invalid SQLAlchemy URL configuration after the shell `python` PATH issue is corrected; offline migration graph/schema tests pass.

## Remaining gates

- Add/run PostgreSQL integration coverage for six-swap replenishment, concurrent exhaustion, downgrade, and unrelated-slot immutability.
- Add direct handler-level coverage for snapshot/history replenishment and metric outcome propagation.
- Run focused Flutter slot-cache tests and staging database-pool/latency observation before release enablement.
