# Release Checklist: Normalized Database Refactor

## Preflight

- Confirm single Alembic head: `alembic heads` should show `20260609000006`.
- Take a database backup before applying migrations in production.
- Count malformed/outlier rows without printing raw JSON/PII:
  - saved suggestions with non-object `suggestion_data`
  - meals with non-array `instructions`
  - food references with non-array `serving_sizes`
  - food references with non-object `extra_nutrients`
  - payout methods outside `momo` and `bank`

## Deploy

- Apply expand migrations with `alembic upgrade head`.
- Deploy dual-write code in the same release.
- Do not drop `suggestion_data`, `meal.instructions`, `food_reference.serving_sizes`, `food_reference.extra_nutrients`, or `payout_requests.payment_details` in this release.

## Smoke Tests

- Save/list/delete a saved suggestion.
- Accept a meal suggestion and verify `meal_instruction_steps` rows exist.
- Lookup a food reference with serving sizes and extra nutrients.
- Request a referral payout and verify masked typed fields.
- Run notification precompute/dispatch smoke against active `user_fcm_tokens`.
- Query hydration daily/weekly endpoints and confirm legacy fallback remains stable.

## Rollback / Forward Fix

- Preferred fix path is forward migration/code patch because expand migrations preserve old columns.
- If app deploy must roll back, old code can still read legacy JSON columns.
- If a new backfill statement fails, fix the migration and rerun; backfills use deterministic inserts and conflict handling.
- Payout check constraints are added `NOT VALID`; validate after cleaning any legacy method/status outliers.

## Contract Follow-up

- After one production observation window, create a separate contract plan to remove or encrypt legacy JSON fields.
- Validate payout constraints after legacy data audit.
- Consider daily summary read models only with query latency evidence.
