# Red-Team Failure-Mode Plan Review

Scope: plan documents only. Live code inspected only to verify failure paths. No plan files changed.

## Findings

### 1. CRITICAL — Slot locking does not protect the shared plan-version update

- **Plan location:** Phase 6, `Architecture` and `Implementation Steps` 2 and 4 (`phase-06-transactional-swap-and-meal-logging.md:31-33,47-49`).
- **Flaw:** The plan locks the owned slot row, then increments a version on the parent plan. Two swaps against different slots lock different rows, so neither transaction serializes the shared plan read-modify-write. The plan does not require locking the parent plan, using an atomic `UPDATE ... SET version = version + 1`, or checking affected-row count against an expected plan version.
- **Concrete failure:** Request A swaps breakfast slot 1 and request B swaps lunch slot 2. Both read plan version 7, each writes 8, and both commit. Both slot changes persist, but the plan has advanced only once. Any response, stale-write check, audit sequence, or client cache keyed by plan version is now false.
- **Codebase evidence:** Runtime sessions use the ordinary SQLAlchemy async session factory with no serializable isolation configured (`src/infra/database/config_async.py:90-125`). Existing balance mutation explicitly locks the shared wallet row before read-modify-write to prevent lost updates (`src/infra/repositories/referral_repository.py:106-130`). UoW commit adds no concurrency protection (`src/infra/database/uow_async.py:126-159`).
- **Required plan correction:** Define one serialization target for every swap in a plan: lock the parent plan before slot selection/version mutation, or use a compare-and-swap atomic parent update and fail/retry when it affects zero rows. Add a concurrent-different-slots integration case, not only same-slot contention.

### 2. HIGH — Create idempotency handles lookup/replay but not the commit-time uniqueness race

- **Plan location:** Phase 5, `Implementation Steps` 1, 2, 5, and 6 (`phase-05-durable-plans-cqrs-and-api.md:47-54`).
- **Flaw:** A unique owner/idempotency constraint plus an initial lookup is insufficient. Two identical requests can both observe no row and build complete aggregates. One loses only when the UoW commits on context exit. The plan specifies replay semantics but no savepoint, `IntegrityError` recovery, transaction restart, or post-conflict fingerprint read.
- **Concrete failure:** Two mobile retries with the same key arrive concurrently. Both spend the generation cost and flush 55 child rows. Winner commits. Loser raises from `__aexit__`, rolls back, and returns a 500/DB conflict instead of the committed replay required by the plan.
- **Codebase evidence:** Repositories flush while `AsyncUnitOfWork.__aexit__` performs the commit and re-raises commit failure (`src/infra/database/uow_async.py:126-156`). The existing guest-quota race path uses a nested transaction specifically so a uniqueness failure can be caught and the committed row re-read under `FOR UPDATE` (`src/api/services/guest_parse_quota.py:57-96`).
- **Required plan correction:** Specify the exact race algorithm: insert idempotency claim in a savepoint (or separate short transaction), catch unique violation, read by owner/key, verify request fingerprint, then replay; different fingerprint returns conflict. Include a real PostgreSQL concurrent-identical-key test.

### 3. HIGH — “Normal meal logging” and same-transaction interaction logging are incompatible as planned

- **Plan location:** Phase 6, `Requirements`, `Architecture`, and `Implementation Step` 5 (`phase-06-transactional-swap-and-meal-logging.md:26-33,50`).
- **Flaw:** The plan simultaneously requires use of the normal meal flow and atomic persistence of meal plus `meal_logged` interaction, but does not define a shared application service/UoW boundary. Sending the existing normal command through the singleton event bus creates a fresh handler UoW and commits the meal separately. Writing through `meal_repository_async.py` inside the new handler can be atomic, but bypasses normal handler behavior such as post-commit cache invalidation and therefore is not the normal flow.
- **Concrete failure:** The meal transaction commits, then interaction insertion fails: a normal meal exists but duplicate-log protection has no committed record, so retry creates another meal. In the reverse ordering, interaction commits but meal creation fails. If the new handler writes the repository directly, daily meal caches can remain stale because normal invalidation runs outside the repository.
- **Codebase evidence:** Event-bus dispatch shallow-copies stateful handlers with a fresh UoW (`src/infra/event_bus/pymediator_event_bus.py:102-127,137-175`). The normal manual-meal handler owns its UoW and invalidates cache only after that UoW commits (`src/app/handlers/command_handlers/create_manual_meal_command_handler.py:44-72`). The repository itself only flushes and never commits or invalidates (`src/infra/repositories/meal_repository_async.py:77-83,163-191`).
- **Required plan correction:** Extract/reuse a meal-materialization application service that accepts the caller's UoW repositories, then perform meal, duplicate-log claim, and interaction writes in one UoW. Run cache invalidation only after successful outer commit. Test injected failure after each write.

### 4. HIGH — Phase 6 creates commands/routes but no handlers or production event-bus registration

- **Plan location:** Phase 6, `Related Code Files` and `Implementation Steps` (`phase-06-transactional-swap-and-meal-logging.md:35-51`).
- **Flaw:** The phase lists two new command definitions and a route modification, but no command-handler files and no modification to `src/api/dependencies/event_bus.py`. Phase 7 later lists `event_bus.py`, but its work is measurement/rollout and does not say to register Phase 6 command handlers. Phase 6 success criteria therefore cannot be met at the end of Phase 6.
- **Concrete failure:** `POST` swap/log endpoints construct new commands and call `event_bus.send`; production returns `ValueError: No handler registered` for both commands. Unit tests that instantiate handlers directly can still pass, masking the composition failure until API/runtime testing.
- **Codebase evidence:** `PyMediatorEventBus.send` rejects every unregistered event type (`src/infra/event_bus/pymediator_event_bus.py:137-143`). Existing meal commands are explicitly registered in the composition root; for example manual meal creation is wired at `src/api/dependencies/event_bus.py:443-449`.
- **Required plan correction:** Add concrete swap/log handler files, imports, constructor dependencies, and explicit composition-root registrations to Phase 6. Add API tests using `get_configured_event_bus`, plus a startup registration assertion.

### 5. HIGH — Production deployment migrates schema but never installs the required catalog

- **Plan location:** Phase 3, `Related Code Files` and `Implementation Steps` 3-6 (`phase-03-immutable-curated-recipe-catalog.md:35-53`); Phase 7, rollout steps (`phase-07-measurement-and-controlled-rollout.md:45-52`).
- **Flaw:** The plan repairs a manual import script but never makes a versioned catalog artifact and import/verification command part of production pre-deploy. The actual production path runs Alembic only. A single-head migration gate proves tables exist, not that the required 72 versions and per-segment capacity exist in the target database.
- **Concrete failure:** Code and migrations deploy successfully with the backend flag off. Operations enable internal accounts. Every create request returns catalog insufficiency because production has empty catalog tables, even though CI passed against seeded test data. Disabling the flag hides the outage but does not establish a usable next rollout.
- **Codebase evidence:** Production container startup explicitly skips migrations because pre-deploy handles them, then starts the app; it invokes no seed/import command (`docker-entrypoint.sh:11-22,34-42`). Production deployment documentation specifies only `python migrations/run.py` (`docs/database-guide.md:168-172,200`). The migration runner performs `command.upgrade(..., "head")` and nothing catalog-specific (`migrations/run.py:181-202`).
- **Required plan correction:** Define a content-addressed catalog release artifact, an explicit production pre-deploy import command, target-DB coverage verification, and an activation gate that refuses enablement unless the expected catalog release is present and complete.

## Unresolved Questions

- Is `plan_version` intended as a global serialization token for all slot mutations, or only presentation metadata? The plan currently uses it like the former but locks like the latter.
- Must recommendation logging reuse the manual-meal command contract, or only produce an ordinary `Meal` aggregate with equivalent post-commit behavior? The transaction design depends on this decision.

**Status:** DONE
**Summary:** Five Critical/High plan flaws verified against current transaction, event-bus, migration, deployment, and meal-persistence behavior. Plan files untouched; report only added.
**Concerns/Blockers:** None.
