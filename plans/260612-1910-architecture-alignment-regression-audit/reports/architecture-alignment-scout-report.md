---
title: "Architecture alignment scout report"
date: "2026-06-12"
scope: "MealTrack backend async/CQRS/runtime/security documentation audit"
---

# Architecture Alignment Scout Report

## Summary

The app runtime is already async and has strong static guardrails. The highest
value work is not another async migration. The remaining work is alignment:
move shared exceptions out of API, shrink import-linter baselines, standardize
background task ownership, add one or two missing static guards, and make cache
invalidation optimization evidence-backed.

## Evidence Read

- `README.md`
- `docs/system-architecture.md`
- `docs/cqrs-guide.md`
- `docs/database-guide.md`
- `docs/architecture/*.md`
- `docs/standards/patterns.md`
- `docs/decisions/260608-2223-selective-cache-admission-policy.md`
- `docs/journals/260610-async-boundary-hygiene.md`
- `src/infra/database/config_async.py`
- `src/infra/database/connection_policy.py`
- `src/infra/database/uow_async.py`
- `src/api/dependencies/event_bus.py`
- `src/infra/event_bus/pymediator_event_bus.py`
- `src/infra/event_bus/background_task_manager.py`
- `src/api/dependencies/task_manager.py`
- `tests/architecture/test_async_boundary_hygiene.py`
- `tests/architecture/test_async_db_runtime_boundaries.py`
- `.importlinter`

## Verification

```bash
.venv/bin/pytest tests/architecture/test_async_boundary_hygiene.py tests/architecture/test_async_db_runtime_boundaries.py -q
```

Result: 14 passed.

```bash
.venv/bin/lint-imports
```

Result: 4 contracts kept, 0 broken.

Note: local `.venv` reported Python 3.13.2 during pytest. Repo runtime target is
Python 3.11, so deploy-readiness should still use a 3.11 environment.

## Current Strengths

- `config_async.py` owns app runtime DB sessions.
- `config.py` is explicitly migration/admin-only.
- `connection_policy.py` makes direct-pool vs Neon-pooler mode explicit.
- `AsyncUnitOfWork` owns commit/rollback/session-close behavior.
- Repositories are guarded against internal transaction boundaries except a
  known pgvector recovery boundary.
- Event bus uses a singleton registry and fresh UoW copies for stateful
  handlers.
- Route-level direct commits, event-loop drivers, route/event-bus unmanaged
  tasks, sync DB imports, and `requests` in async adapters are already tested.
- Redis cache policy is selective and documented.

## Findings

### P1: Shared exceptions live under API

App and infra files import `src.api.exceptions`. The classes are reusable
application exceptions, but their module name and dependency direction are
wrong for clean architecture.

Examples:

- `src/app/handlers/command_handlers/update_custom_macros_command_handler.py`
- `src/app/handlers/query_handlers/get_meal_by_id_query_handler.py`
- `src/infra/event_bus/pymediator_event_bus.py`
- `src/infra/services/feature_flag_service.py`

Impact: new features may keep copying an API-owned exception dependency into
app/infra. This keeps `.importlinter` baselines larger than they should be.

Recommended plan: move exception classes to app/domain, leave HTTP conversion in
API, then shrink import-linter baselines.

### P1: App-to-infra baselines are green but broad

`lint-imports` passes, but `.importlinter` intentionally freezes many direct
`src.app -> src.infra` imports. That is a transition baseline, not the desired
pattern.

Impact: future handlers can look at existing direct `AsyncUnitOfWork` or model
imports and copy them. The rule should be "do not grow the baseline."

Recommended plan: migrate touched slices behind ports/UoW abstractions and
remove ignore lines as each slice lands.

### P2: Gemini refresh task has a separate ownership model

The event bus uses `BackgroundTaskManager`, but
`GeminiCacheManager.start_refresh_loop()` calls `asyncio.create_task()` and
tracks its own task. Lifespan stops it, so this is controlled today, but it is a
separate pattern.

Impact: future refresh loops may copy the raw task pattern instead of using the
process manager.

Recommended plan: route refresh-loop ownership through the process task manager
or make lifespan own the coroutine directly.

### P2: Sync HTTP guard does not catch sync `httpx`

Architecture tests block `requests` imports in async adapters. Current source
also contains sync `httpx.get/head` in `CloudinaryImageStore`, but those calls
are wrapped by async methods with `asyncio.to_thread`. The wrapper is safe, yet
the guardrail would not catch a future sync `httpx` call placed directly in an
async path.

Impact: an async route/handler could block the event loop with sync `httpx`.

Recommended plan: add a static guard for sync `httpx.*` calls in runtime
adapter paths unless the call is inside a sync method that is only reached via
`to_thread`.

### P2: Cache invalidation can be latency-heavy

The manual-save journal already identified 6-8 sequential Redis invalidation
round-trips. This is correct for freshness, but can become visible latency.

Impact: post-write endpoints can wait on Redis. If Redis is slow, manual saves,
hydration writes, and movement writes may feel sluggish.

Recommended plan: monitor `cache_ms`; batch with pipeline/`UNLINK` only when
production evidence proves the need.

### P3: Connection pool docs had stale fixed numbers

The live policy uses env-driven worker and pool sizing. Any docs that still use
fixed connection counts should point to the formula.

Impact: operators could size Render/Neon incorrectly.

Recommended plan: keep all docs aligned to `connection_policy.py` and
`docs/database-guide.md`.

## Security Threat Model Notes

Primary assets:

- User nutrition, profile, weight, hydration, movement, subscription, and
  notification data.
- Firebase identity mapping and admin-only controls.
- RevenueCat subscription/webhook state.
- Affiliate event outbox integrity.
- Cloudinary image references and upload signatures.
- External API keys and service-account credentials.

Trust boundaries:

- Public mobile/API traffic crosses Firebase auth and per-user ownership checks.
- Admin operations cross `require_admin`.
- RevenueCat webhooks cross webhook secret validation.
- Affiliate dispatch crosses HMAC-signed internal API calls.
- Redis is an optimization or required transient state depending on key family.
- DB migrations use a separate migration/admin connection path.

Relevant attacker stories:

- Authenticated user attempts cross-user meal/profile/notification access.
- Client tampers with image IDs, Cloudinary URLs, or direct-upload signatures.
- External actor replays or forges webhook/affiliate requests.
- Malicious or buggy client causes expensive AI/image/search paths repeatedly.
- Operator misconfigures CORS, DB pool mode, or Redis dependency behavior.

Existing controls:

- Firebase auth dependencies and dev-auth bypass isolation.
- `require_admin` for feature flag mutations.
- RevenueCat and affiliate integration boundaries.
- Import-linter and architecture tests for runtime boundaries.
- Cache admission ADR for Redis usage.
- Structured timing logs that avoid raw payload logging on manual save paths.

## Recommended Execution Order

1. Exception boundary relocation.
2. App-to-infra baseline shrink for touched feature areas.
3. Background task ownership alignment.
4. Cache invalidation batching only if production timing logs justify it.
5. External trust-boundary audit before touching RevenueCat webhook, affiliate,
   payout, or image upload flows.
6. Static guard expansion.

## Unresolved Questions

None.
