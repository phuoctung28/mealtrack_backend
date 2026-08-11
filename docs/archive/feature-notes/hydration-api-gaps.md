**Status:** Archived feature note — not evergreen authority
**Evergreen:** `docs/system-architecture.md`, `docs/api-endpoints.md`, `docs/codebase-summary.md`

# Hydration API - Historical Gap Review

**Created:** 2026-05-23  
**Updated:** 2026-07-29
**Status:** Historical. The backend now implements the hydration catalog, daily summary, weekly summary, streak, and delete semantics described in [api-hydration.md](./api-hydration.md).

---

## What Changed Since the Original Gap Review

| Topic | Current state |
|-------|---------------|
| Catalog | `GET /v1/hydration/catalog` is implemented and returns the visible catalog. |
| Daily summary | `GET /v1/hydration/daily` returns `consumed_ml`, `goal_ml`, `percentage`, `streak`, and entries. |
| Weekly summary | `GET /v1/hydration/weekly` returns a 7-day chart with `week_start`, `goal_ml`, and per-day totals. |
| Delete | `DELETE /v1/hydration/{entry_id}` soft-deletes normalized entries and deactivates a linked legacy hydration meal when present. |

---

## Current Catalog Shape

The active catalog has 13 visible drinks plus one internal `scanned` alias used by AI-scanned beverage flows. The public catalog endpoint returns the 13 visible drinks; the alias is not listed in the response.

---

## Response Semantics

- `consumed_ml` is the sum of `credited_ml` for non-deleted entries in the local day window.
- `goal_ml` comes from the user profile override when present, otherwise from the 35 ml/kg fallback.
- `percentage` is derived from `consumed_ml / goal_ml` and is not capped in the backend response.
- `streak` is computed from the merged normalized and legacy history windows, ending on or before today.

---

## Historical Notes

The original gap list still matters as design history, but it should no longer be treated as an active implementation backlog. Keep this file for provenance only and use [api-hydration.md](./api-hydration.md) as the current contract source.
