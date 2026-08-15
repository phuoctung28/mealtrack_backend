# Phase 4: Canonical Nutrition Integrity

Phase 4 closed on 2026-08-15 on `feature/canonical-nutrition-integrity-phase-04`.

The manual create/edit contract now has an explicit v2 version and origin matrix.
References are resolved by `ManualMealNutritionResolver`; local and USDA items
must be verified and provider items must return the requested identity. Client
nutrition, gram weights, and serving conversions are not authoritative. Explicit
user-entered overrides remain bounded exceptions and retain the immutable source
snapshot needed to clear the override.

Successful v2 writes persist source identity, contract version, backend nutrition,
serving conversions, and an immutable source snapshot. Snapshot serving weights
are also used during aggregation; unsupported units fail closed. Reads prefer the
snapshot, so later reference changes cannot rewrite an existing meal detail
response. The durable write-operation table provides user-scoped fingerprints,
replay responses, leases, fencing generations, and bounded terminal-record
cleanup for idempotent create/edit retries. The capability route verifies all
required snapshot and replay columns before advertising support.

Validation: focused Phase 4 regression tests passed (109 tests); the CI-aligned
unit gate passed 2360 tests with 44 warnings at 78.83% coverage; compileall and
scoped Ruff checks passed. Alembic heads were valid, but migration SQL generation
could not run to a database because this checkout has no valid `DATABASE_URL`; no
migration was applied locally. Existing unrelated onboarding/cron WIP remained
unstaged.

The broader integration attempt was not a clean signal: the test database lacks
existing `users.revenuecat_customer_id` and `nutrition.nutrition_override`
columns, development-user authentication therefore returned 401/500, and one
unrelated baseline test referenced a missing `authenticated_client` fixture.

Next: apply and round-trip the migration in a configured PostgreSQL environment,
then observe the additive v2 contract before the Flutter cutover.
