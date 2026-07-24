# Meal Catalog Incident Runbook

Use this for catalog import, local-first food search, or catalog-backed
recommendation incidents.

## Severity Guide

| Severity | Examples |
|---|---|
| Sev1 | Recommendation endpoint has sustained 5xx, catalog snapshot cold-start failure, or migration blocks production startup. |
| Sev2 | Provider outage causes degraded search, high latency, or recommendation create p95 above 1.5 s. |
| Sev3 | Import dry-run finds unresolved ingredients, near duplicates, or missing coverage before production import. |

## Triage

1. Check `/health` and Render deploy status.
2. Check Alembic head and migration logs.
3. Check these metrics:
   - `meal_catalog.snapshot.refresh`
   - `meal_catalog.snapshot.active_meals`
   - `meal_catalog.snapshot.age_seconds`
   - `food_search.requests`
   - `meal_recommendation.requests`
4. Confirm whether the issue affects create, replay/read, slot detail, swap,
   log, skip, food search, or import only.

## Decision Tree

1. If the issue is provider-only and local search still works, follow
   [Provider Outage](./provider-outage.md).
2. If recommendation create fails but replay/read still works, stop exposing new
   recommendation creation and keep existing plan reads available.
3. If a new deploy caused errors, restore the previous GHCR SHA in Render.
4. If catalog content caused incorrect recommendations, prepare reviewed SQL to
   set affected additive catalog rows `is_active=false`. Include the selection
   criteria, expected row count, rollback SQL, and reviewer sign-off.
5. If migration state blocks startup, follow
   [Render CD Flow](../guides/render-cd.md#emergency-recovery).

## SQL Safety

Use read-only count queries first. For catalog deactivation, prefer a transaction
with explicit `RETURNING` evidence:

```sql
begin;

select id, catalog_key
from meal_catalog
where catalog_key = any(:catalog_keys)
  and is_active is true;

update meal_catalog
set is_active = false
where catalog_key = any(:catalog_keys)
  and is_active is true
returning id, catalog_key;

rollback;
```

Replace `rollback` with `commit` only after the reviewed output matches the
expected row count.

## Closeout

Record UTC timeline, impact, root cause, metrics before/after, actions taken,
and follow-up owners. Exclude raw meal payloads, search terms, tokens, database
URLs, user IDs, and provider credentials.
