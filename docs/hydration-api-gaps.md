# Hydration API Gap Review

**Created:** 2026-05-23
**Last Reviewed:** 2026-06-27
**Status:** Archival. The original mobile-blocking gaps are resolved in the current backend.

---

## Resolved Items

- `GET /v1/hydration/weekly` exists and returns server-backed weekly history.
- `GET /v1/hydration/daily` includes the current streak.
- `POST /v1/hydration/log` and `POST /v1/hydration/log/drink` return `id` and full hydration-entry fields.
- `DELETE /v1/hydration/{entry_id}` returns `{ "success": true }`.
- `daily_water_goal_ml` is profile-backed with a 2000 ml fallback.
- Catalog category now treats `coke-zero` as hydration, not caloric.

---

## Current Notes

- `POST /v1/hydration/log` still creates a legacy hydration meal row for compatibility and returns its ID in `meal_id`.
- `POST /v1/hydration/log/drink` writes normalized hydration state only; `meal_id` remains a compatibility alias for the hydration entry ID.
- The catalog currently exposes 12 public drinks plus a virtual `scanned` drink used for historical scanned beverage rows.

---

## Remaining Follow-Up

- Keep `docs/api-hydration.md` as the live contract.
- Re-check mobile parsing before removing legacy compatibility fields from hydration responses.
