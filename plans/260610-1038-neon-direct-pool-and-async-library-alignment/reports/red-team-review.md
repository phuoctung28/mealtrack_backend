---
type: red-team
topic: neon direct pool and async library alignment
created: "2026-06-10"
---

# Red-Team Review

## Finding 1: Direct Pool Can Exhaust Neon

Direct URL + app pooling removes PgBouncer prepared-statement risk but moves
connection-budget ownership to the app. Bad worker/pool defaults can hit Neon
`max_connections`.

Mitigation: require small defaults, health visibility, and rollout checklist.

## Finding 2: Pooler Mode Must Not Be Half-Safe

Supporting pooler mode without prepared-statement safeguards invites the exact
asyncpg/PgBouncer failure this plan is meant to avoid.

Mitigation: tests must assert `NullPool` plus prepared-statement-safe settings.

## Finding 3: Cloudinary Is Not Truly Async

Changing interfaces to `async def` while still calling sync SDK functions would
only hide blocking behavior.

Mitigation: use `asyncio.to_thread` / executor wrappers at the adapter boundary
and document vendor SDK limitation.

## Finding 4: Env Compatibility Can Mask Bad Prod Config

Keeping fallback env names is useful for local dev, but in production it can
hide incorrect deployment state.

Mitigation: production mode should fail fast on ambiguous unsafe env combos and
log selected source/mode with sanitized host only.

## Finding 5: Removing `requests` Too Early Can Break Scripts

`requests` may remain useful for tests/scripts or transitive behavior. A broad
dependency removal can create noisy failures unrelated to runtime async safety.

Mitigation: remove active runtime imports first; remove dependency only after
static scan proves no active source path needs it.

## Overall Verdict

Plan is viable if implemented as explicit policy + tests, not as a quick env
rename. Highest-risk item is connection budget; second-highest is Cloudinary
interface churn.
