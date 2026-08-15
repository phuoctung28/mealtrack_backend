# Phase 3 Canonical Nutrition Integrity

**Date**: 2026-08-15 15:15
**Severity**: Medium
**Component**: canonical nutrition search and source resolution
**Status**: Resolved

## What Happened

Phase 3 finished the search/source-resolution pass for canonical nutrition integrity. We made search and parse carry additive origin fields instead of dropping identity, added `source_namespace` and `source_food_id` to persisted food references, and kept local results gated by the shared integrity policy instead of trusting whatever happened to be ranked first.

## The Brutal Truth

This was overdue cleanup of a broken trust boundary. The system had been losing canonical identity in transit, then pretending the remaining data was good enough. That is how bad nutrition data leaks downstream and becomes somebody else’s headache later.

## Technical Details

- Search/parse now returns one logical origin plus additive identity fields: `origin`, `food_reference_id`, namespaced `food_id`, and nutrition basis/version.
- `food_reference.source_namespace` and `food_reference.source_food_id` round-trip through the repository and dedupe independently of display name.
- Local search applies `nutrition_integrity_v1` before final dedupe/limit, continuing candidate batches until valid results fill the limit or candidates are exhausted so invalid high-ranked rows do not crowd out valid ones.
- Provider results without an opaque source ID degrade to the AI path instead of claiming provider authority; source-identity renames remain explicit review collisions.
- Search cache keys include both the response schema version and `nutrition_integrity_v1`.
- Validation evidence: `64 passed` focused Phase 3 tests, `2330 passed` in the filtered unit gate, coverage `79.55%`, and `10/10` offline synthetic evaluator cases passed.

## What We Tried

We kept the change additive instead of ripping out old response keys. That preserved compatibility while moving the real authority into the backend. We also reused the shared policy instead of duplicating integrity checks in search and parse paths.

## Root Cause Analysis

The real bug was identity loss plus weak read-time enforcement. Once canonical origin disappeared, downstream code had no reliable way to tell a valid reference from a semantically bad one, and ranking could surface the wrong thing.

## Lessons Learned

Never let normalized display text stand in for durable source identity. If the backend owns nutrition truth, then the backend has to carry the identity and enforce the policy all the way through the read path.

## Next Steps

Phase 4 is next: make manual save reference-authoritative so save paths use backend-resolved canonical identity instead of client-authored nutrition. The unrelated cron/onboarding WIP failure in `tests/unit/cron/test_push_cron.py::test_push_cron_phase_failure_does_not_abort_subsequent_phases` is still real, but it is separate from this work.

**Status:** DONE
**Summary:** Phase 3 normalized search and source resolution, preserved canonical identity through additive contracts, and passed focused validation; the remaining cron failure is unrelated WIP, and Phase 4 is manual-save authority.
