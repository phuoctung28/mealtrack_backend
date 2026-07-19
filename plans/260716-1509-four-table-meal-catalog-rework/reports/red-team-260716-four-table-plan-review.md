---
type: red-team
date: 2026-07-16
status: resolved
reviewed: true
---

# Red Team: Four-Table Meal Catalog Rework

## Findings

1. Critical: full historical swap replay cannot survive without an operation-history table.
2. High: old release/version response identifiers needed an explicit unshipped-contract migration.
3. High: repeated batch metadata needed an enforceable 3NF-safe representation.
4. High: `shown_at` needed a CQRS-compliant write path.
5. Medium: query-handler, analytics, history-projector, exports, and stale-symbol inventories were incomplete.
6. Medium: exact recommendation columns and outcome transitions were underspecified.

## Resolutions

- Batch metadata moved to one self-referenced anchor candidate row.
- User approved `meal_recommendation_operations`; create/swap/skip/log requests retain full historical replay and payload-conflict validation.
- Phase 1 now gates removal/rename of unshipped response fields and provides a compatibility fallback if a client already consumes them.
- Added owner-scoped idempotent shown command, explicit skip command, terminal-state rules, exact constraints, and missing caller/test inventories.
- Added whole-plan stale-symbol sweep.

## Unresolved Questions

None.
