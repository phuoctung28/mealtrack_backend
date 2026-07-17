# Single-Thread Chatbot Implementation Plan — Delivery

**Prerequisite:** complete [Foundation Plan](./implementation-plan-foundation.md).

## Task 6 — Application Orchestration and CQRS

Create commands, query, handlers, and `ChatOrchestrationService`.

### Send Turn

- [ ] Validate command data at command/domain boundary.
- [ ] Phase A: open UoW, reserve thread/message pair, commit, close.
- [ ] Return completed same-ID replay immediately.
- [ ] Return controlled busy/conflict without an AI call.
- [ ] Phase B: load history/context in short read UoW(s), then close.
- [ ] Assert in tests that no UoW/session is open during `ChatCompletionPort`.
- [ ] Apply safety and context-window policies.
- [ ] Phase C success: finalize the reserved assistant row in a new UoW.
- [ ] Phase C failure: mark the same row failed with a safe code, commit, then raise a controlled exception.
- [ ] Retry final DB write once for a transient persistence failure without creating a new row.

### Read History

- [ ] Keep `GetChatThreadQuery` side-effect free.
- [ ] Return null thread/empty page when absent.
- [ ] Enforce page size and sequence cursor.

### Clear

- [ ] Delete only the authenticated user's thread.
- [ ] Succeed when absent.
- [ ] Reject during a non-stale active generation.

### CQRS Registration

- [ ] Register handlers on the configured singleton event bus.
- [ ] Inject UoW factories and domain ports at the composition root.
- [ ] Preserve handler cloning/fresh UoW behavior.
- [ ] Do not instantiate infrastructure inside app handlers.
- [ ] Do not log before re-raising.

**Exit:** every orchestration state/failure path is unit-tested and import-linter needs no new baseline.

## Task 7 — API, Gate, and Error Mapping

- [ ] Implement only:
  - `GET /v1/chat/thread`
  - `POST /v1/chat/messages`
  - `DELETE /v1/chat/thread`
- [ ] Require `get_current_user_id` everywhere.
- [ ] Reject extra request fields.
- [ ] Reuse Accept-Language middleware.
- [ ] Apply per-authenticated-user rate limiting; verify the key is not merely IP-based.
- [ ] Gate with `CHAT_ENABLED` plus optional `CHAT_BETA_USER_IDS`.
- [ ] Map domain outcomes to approved codes/statuses.
- [ ] Add chat-specific unavailable copy; never return meal-generation wording.
- [ ] Exclude provider/usage/error metadata from public responses.
- [ ] Register the router only after dependency composition succeeds.
- [ ] Update smoke and OpenAPI tests.

**Exit:** API tests prove auth, gate, ownership, schema, pagination, idempotency, busy, rate limit, unavailable, and clear behavior.

## Task 8 — Observability, Privacy Guards, and Cost Controls

- [ ] Emit approved content-free counters/histograms through `src.observability`.
- [ ] Use only allowlisted scalar attributes.
- [ ] Measure total turn latency separately from provider latency.
- [ ] Record provider token usage when available.
- [ ] Record context truncation/partial availability without values.
- [ ] Add product analytics only after privacy/product approval; never attach content.
- [ ] Extend static logging guards for chat content/prompt/context fields.
- [ ] Test that exception strings exclude user text and raw provider output.
- [ ] Verify OpenTelemetry/PostHog LLM instrumentation does not collect payload content.
- [ ] Add disabled-by-default kill switch and empty allowlist.
- [ ] Before cohort expansion, add durable daily quota and cost alerting.

**Exit:** staging telemetry audit finds zero raw content and all planned metrics are visible.

## Task 9 — Verification

### Narrow suites

- [ ] `pytest tests/unit/domain/chat -q`
- [ ] `pytest tests/unit/app/chat -q`
- [ ] `pytest tests/unit/infra/chat -q`
- [ ] `pytest tests/unit/api/chat -q`
- [ ] `pytest tests/integration/infra/test_chat_repositories.py -o addopts="" -m integration -q`
- [ ] `pytest tests/integration/api/test_chat_api.py -o addopts="" -m integration -q`
- [ ] Alembic upgrade/downgrade/upgrade check

### Repository gates

- [ ] `lint-imports`
- [ ] `ruff check src tests`
- [ ] `black --check src tests`
- [ ] `mypy src`
- [ ] `pytest tests/unit --cov=src --cov-fail-under=65`
- [ ] New feature coverage ≥90%; critical correctness branches fully covered where practical.

### Manual staging checks

- [ ] First message and personalized response.
- [ ] Restart and history recovery.
- [ ] Same-ID replay after simulated network timeout.
- [ ] Concurrent sends.
- [ ] Provider timeout/fallback/unavailable.
- [ ] Failed same-ID retry.
- [ ] Clear and account deletion.
- [ ] Approved multilingual/safety prompt evaluation.
- [ ] Log/trace/analytics redaction audit.

**Exit:** all gates in [Testing and Rollout](./testing-and-rollout.md) pass.

## Task 10 — One-User Production Beta

- [ ] Apply migration while `CHAT_ENABLED=false`.
- [ ] Deploy code with empty allowlist.
- [ ] Verify health, router composition, and dashboards.
- [ ] Add exactly one approved internal `users.id`.
- [ ] Enable global flag.
- [ ] Run production beta scenarios.
- [ ] Review daily aggregate usage, latency, failures, busy conflicts, stale recovery, and cost.
- [ ] Keep a documented rollback owner and config path.
- [ ] Disable immediately for privacy, safety, duplication, or cross-user anomalies.

**Beta exit:** explicitly choose stop, iterate, or proceed to a small internal cohort. No automatic expansion.

## Task 11 — Broader-Release Readiness

- [ ] Implement approved retention cleanup.
- [ ] Implement durable daily message/token quota.
- [ ] Complete seven-language safety and UX review.
- [ ] Add user-facing AI disclosure and retention explanation.
- [ ] Add support/incident runbook.
- [ ] Confirm provider privacy/retention settings.
- [ ] Set daily/monthly cost budget and alerts.
- [ ] Update README, roadmap, codebase summary, architecture, endpoint counts, and external-service docs only after the feature is live.
- [ ] Correct stale historical chat claims.

Streaming, multiple threads, tools, RAG, images, and proactive chat each require a separate design.

## Recommended Pull Request Slicing

### PR A — Domain and Persistence

- domain contracts/policies;
- migration and ORM;
- repositories/UoW;
- PostgreSQL and migration tests;
- no accessible route.

### PR B — Deterministic Vertical Slice

- application orchestration;
- REST API and gate;
- fake completion adapter;
- full deterministic tests;
- production disabled.

### PR C — Provider, Context, and Operations

- managed provider adapter;
- versioned prompt;
- MealTrack context reader;
- safety evaluation;
- telemetry/redaction;
- staging only.

### PR D — One-User Beta Readiness

- dashboards/runbook;
- empty-by-default allowlist;
- production enablement and rollback procedure;
- no scope expansion.

Each PR must leave the service deployable and independently reviewable.

## Definition of Done

- [ ] Approved API/data/AI contracts remain unchanged or are re-approved.
- [ ] One thread per user and one active turn per thread are database-enforced.
- [ ] Completed same-ID replay duplicates neither messages nor provider work.
- [ ] Provider calls hold no DB transaction/session.
- [ ] Ownership and delete cascades are proven in integration tests.
- [ ] Controlled failures leave retryable durable state.
- [ ] Raw chat/context data appears nowhere in telemetry.
- [ ] Safety and language evaluations meet threshold.
- [ ] Architecture, lint, type, and test gates pass.
- [ ] Production access is limited to the approved beta user.
- [ ] Rollback was exercised.