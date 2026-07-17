# Single-Thread Chatbot Implementation Plan

> **For implementers:** execute this plan task-by-task. Keep pull requests reviewable, preserve the documented contracts, and do not add chatbot behavior beyond the approved MVP.

**Goal:** Deliver an authenticated, persistent, read-only MealTrack chatbot with one thread per user and an initial one-user production allowlist.

**Architecture:** FastAPI REST → CQRS command/query handlers → `ChatOrchestrationService` → async UoW repositories, bounded MealTrack context reader, and provider-neutral `ChatCompletionPort`. PostgreSQL enforces ownership, ordering, idempotency, and one active generation per thread. AI calls occur outside database transactions.

**Tech stack:** Python 3.13, FastAPI, Pydantic 2, async SQLAlchemy/PostgreSQL, Alembic, PyMediator, LangChain/provider adapters, existing observability facade, pytest.

**Design references:** [Overview](./README.md) · [Architecture](./architecture.md) · [API/Data Contracts](./api-and-data-contracts.md) · [Operations/Testing/Rollout](./operations-testing-rollout.md)

---

## Scope Guardrails

- [ ] One authenticated user may own at most one thread.
- [ ] Initial production access is one allowlisted internal user.
- [ ] Text only; synchronous complete response.
- [ ] Read-only personalization; no AI tools or mutations.
- [ ] No Redis dependency for durable state or correctness.
- [ ] No new `.importlinter` exemptions.
- [ ] No raw chat content in logs, telemetry, analytics, or exception messages.
- [ ] Do not update README/roadmap to claim live chat until the feature is deployed and enabled.

---

## Planned File Map

Exact package splitting may be adjusted to keep files below repository size limits, but responsibilities must remain separated.

```text
src/api/
├── routes/v1/chat.py
├── schemas/request/chat_requests.py
├── schemas/response/chat_responses.py
├── mappers/chat_mapper.py
└── dependencies/chat.py

src/app/
├── commands/chat/
│   ├── send_chat_message_command.py
│   └── clear_chat_thread_command.py
├── queries/chat/get_chat_thread_query.py
├── handlers/command_handlers/chat/
│   ├── send_chat_message_command_handler.py
│   └── clear_chat_thread_command_handler.py
├── handlers/query_handlers/chat/get_chat_thread_query_handler.py
└── services/chat/chat_orchestration_service.py

src/domain/
├── model/chat/
│   ├── chat_thread.py
│   ├── chat_message.py
│   └── chat_completion.py
├── ports/
│   ├── chat_thread_repository_port.py
│   ├── chat_message_repository_port.py
│   ├── chat_completion_port.py
│   └── chat_context_reader_port.py
├── services/chat/
│   ├── chat_context_window_policy.py
│   └── chat_safety_policy.py
└── exceptions/chat_exceptions.py

src/infra/
├── database/models/chat_thread.py
├── database/models/chat_message.py
├── repositories/chat_thread_repository_async.py
├── repositories/chat_message_repository_async.py
├── services/ai/managed_chat_completion_adapter.py
├── services/ai/prompts/chat_system_prompt.py
└── adapters/chat_context_reader.py

migrations/versions/<next_revision>_add_chat_tables.py

tests/
├── unit/api/chat/
├── unit/app/chat/
├── unit/domain/chat/
├── unit/infra/chat/
├── integration/api/test_chat_api.py
├── integration/infra/test_chat_repositories.py
└── migrations/test_chat_tables_migration.py
```

Existing files expected to change:

- `src/api/main.py`
- `src/api/dependencies/event_bus.py`
- `src/api/base_dependencies.py` or a smaller chat-specific composition module
- `src/domain/model/ai/model_purpose.py`
- `src/domain/ports/async_unit_of_work_port.py`
- `src/infra/database/uow_async.py`
- `src/infra/database/models/__init__.py`
- `src/infra/config/settings.py`
- exception registration/mapping files as needed
- model-registry, architecture, and smoke-route tests

---

## Task 0 — Baseline and Contract Approval

**Purpose:** avoid implementing against stale documentation or an unapproved product contract.

- [ ] Confirm `delivery` is the implementation base and record current Alembic head.
- [ ] Confirm no active chat router/runtime subsystem exists despite historical README/roadmap wording.
- [ ] Approve the three endpoints and public message schema.
- [ ] Approve one-user allowlist semantics and feature-disabled response.
- [ ] Decide whether today's macro snapshot is enabled in beta.
- [ ] Approve input/output/history/timeout defaults.
- [ ] Approve health, emergency, eating-disorder, and read-only copy in all supported languages or explicitly restrict the first beta language.
- [ ] Document temporary beta retention exception and owner.
- [ ] Define the prompt-evaluation pass threshold.

**Exit criteria:** all open review decisions in `README.md` have named owners and approved answers.

---

## Task 1 — Domain Model, Policies, Ports, and Exceptions

**Create:** domain files listed above.

- [ ] Define `ChatRole` (`user`, `assistant`) and `ChatMessageStatus` (`generating`, `completed`, `failed`) enums.
- [ ] Define `ChatThread` with owner ID, next sequence, timestamps, and sequence allocation behavior.
- [ ] Define `ChatMessage` with role/status transition invariants.
- [ ] Define provider-neutral completion request/result DTOs; no LangChain/OpenAI types.
- [ ] Define repository ports around use cases rather than exposing SQLAlchemy query primitives.
- [ ] Define `ChatContextReaderPort` and minimal allowlisted snapshot DTO.
- [ ] Define `ChatCompletionPort` with role-preserving history and deadline/output limits.
- [ ] Implement deterministic context-window policy using message and character caps.
- [ ] Implement input/output safety policy hooks and safe failure classifications.
- [ ] Add chat-specific domain exceptions and stable error codes.
- [ ] Add complete domain unit tests before infrastructure work.

**Required invariants:**

- user messages can only be completed and non-empty;
- assistant messages require a reply target;
- completed assistant messages have visible content;
- failed messages expose only a safe error code;
- failed assistant → generating retry is allowed; completed messages are immutable;
- system/context/tool messages are not visible persisted domain messages.

**Exit criteria:** domain tests pass with no external imports and no app/API/infra dependencies.

---

## Task 2 — Alembic Migration and ORM Models

**Create:** two ORM models and one Alembic revision.  
**Modify:** model registry.

- [ ] Add `chat_threads` exactly as approved in the data contract.
- [ ] Add `chat_messages` exactly as approved in the data contract.
- [ ] Use timezone-aware timestamps.
- [ ] Add cascading foreign keys from user → thread → messages.
- [ ] Add unique thread owner, sequence, client-message, and reply-target constraints.
- [ ] Add PostgreSQL partial unique index for one generating assistant per thread.
- [ ] Add latest-history and stale-generation indexes.
- [ ] Add database checks for role/status/content coherence where practical.
- [ ] Register both models in `src/infra/database/models/__init__.py` so Alembic metadata and tests see them.
- [ ] Add migration tests that inspect tables, FKs, unique/check constraints, and indexes.
- [ ] Run upgrade → downgrade one revision → upgrade against a disposable PostgreSQL database.

**Do not:** use Redis, create a summary/vector table, add thread title/archive fields, or store rendered prompts.

**Exit criteria:** migration is reversible, model metadata includes both tables, and account-delete cascade is proven.

---

## Task 3 — Async Repositories and Unit of Work

**Create:** async thread/message repositories.  
**Modify:** UoW port and concrete UoW.

- [ ] Add typed chat repository properties to `AsyncUnitOfWorkPort`.
- [ ] Initialize concrete repositories in `AsyncUnitOfWork._init_repositories()`.
- [ ] Keep repositories commit-free; UoW owns transaction completion.
- [ ] Implement get-by-user and create-one-thread behavior.
- [ ] Implement thread row locking for reservation and sequence allocation.
- [ ] Implement atomic reservation of user plus assistant placeholder.
- [ ] Translate expected unique/partial-index conflicts into domain outcomes, not raw `IntegrityError` leaks.
- [ ] Implement exact idempotency lookup and content conflict detection.
- [ ] Implement completed-pair lookup for replay.
- [ ] Implement failed-placeholder re-reservation.
- [ ] Implement assistant finalize/fail transitions with ownership checks.
- [ ] Implement stale-generation recovery by lease timestamp.
- [ ] Implement cursor pagination ordered by sequence.
- [ ] Implement idempotent thread hard-delete.
- [ ] Add PostgreSQL integration tests, including concurrent reservations from separate sessions.

**Critical test:** two workers racing to create/reserve the same user's thread must yield one valid thread and one controlled busy/idempotent outcome, never duplicate rows.

**Exit criteria:** repository integration suite passes against PostgreSQL and no sync DB code is added.

---

## Task 4 — Chat Prompt and Managed AI Adapter

**Create:** versioned prompt module and `ChatCompletionPort` implementation.  
**Modify:** model purpose/routing and composition settings.

- [ ] Add `ModelPurpose.CHAT` without changing existing purpose behavior.
- [ ] Keep the static chat system prompt in one versioned source.
- [ ] Represent system instructions, context data, history, and current message as separate structured roles/blocks.
- [ ] Mark the MealTrack snapshot as untrusted data, not instructions.
- [ ] Use existing configured text model/provider ownership by default.
- [ ] Reuse circuit-breaker/fallback patterns where they preserve structured roles.
- [ ] Use chat-specific purpose metadata for prompt cache and telemetry.
- [ ] Force provider response storage off in production chat calls.
- [ ] Apply output-token and provider-timeout limits.
- [ ] Normalize provider success into content, model/provider, usage, latency, and finish reason.
- [ ] Classify timeout, rate limit, unavailable, invalid/empty output, truncation, and unknown failures.
- [ ] Never return raw SDK/LangChain response objects above infrastructure.
- [ ] Add adapter unit tests with mocked providers for success, fallback, timeout, empty output, token metadata, and redaction.
- [ ] Add prompt contract tests for version, static/dynamic separation, read-only rule, and prohibited secrets/identifiers.

**Architecture check:** do not merely concatenate history into the existing general prompt string; preserve role boundaries.

**Exit criteria:** fake and mocked-provider tests pass; no live provider call is required by default tests.

---

## Task 5 — MealTrack Context Reader

**Create:** bounded read adapter and associated DTO mapping.

- [ ] Resolve language through existing request/profile fallback rules.
- [ ] Resolve timezone and local date through existing timezone utilities.
- [ ] Read only approved profile goal/preferences and targets.
- [ ] Read today's aggregate consumed/remaining macros through existing domain/repository behavior, not API DTO reuse.
- [ ] Add `as_of` and availability flags.
- [ ] Omit absent data instead of inventing defaults that look user-specific.
- [ ] Ensure no email, Firebase UID, internal ID, raw meal, image URL, subscription/referral, or notification data enters the snapshot.
- [ ] Make independently optional sections degrade without failing the entire turn.
- [ ] Add unit tests for complete, partial, missing-profile, invalid-timezone, and service-failure snapshots.

**Exit criteria:** snapshot serialization matches the approved allowlist and privacy tests reject prohibited fields.

---

## Task 6 — Application Orchestration and CQRS Handlers

**Create:** commands, query, handlers, and orchestration service.

### Send Turn

- [ ] Validate command data in the command/domain boundary.
- [ ] Phase A: open UoW, reserve thread/message pair, commit, close.
- [ ] Return existing completed pair immediately on idempotent replay.
- [ ] Return controlled busy/conflict outcomes without an AI call.
- [ ] Phase B: load history/context in short read UoW(s), close them.
- [ ] Assert/test that no UoW is open while invoking `ChatCompletionPort`.
- [ ] Apply safety and context-window policies.
- [ ] Phase C success: open new UoW, finalize existing assistant row, commit.
- [ ] Phase C failure: open new UoW, mark the same row failed with safe code, commit, then raise mapped controlled exception.
- [ ] Apply one bounded finalization retry for transient DB errors without creating a new message.

### Read History

- [ ] Keep `GetChatThreadQuery` side-effect free.
- [ ] Return null thread/empty page when absent.
- [ ] Enforce page limits and cursor semantics.

### Clear

- [ ] Delete only the authenticated user's thread.
- [ ] Return success when absent.
- [ ] Reject clear during a non-stale active generation.

### CQRS Registration

- [ ] Register command/query handlers on the configured singleton event bus.
- [ ] Inject factories/ports at the composition root.
- [ ] Ensure handler cloning/fresh UoW behavior remains correct.
- [ ] Do not instantiate concrete infrastructure inside app handlers.
- [ ] Do not log before re-raising.

**Exit criteria:** orchestration unit tests cover every state/failure branch and import-linter passes without new baselines.

---

## Task 7 — API Schemas, Routes, Feature Gate, and Error Mapping

**Create:** chat request/response schemas, mapper, router, and gate dependency.  
**Modify:** router registration and exception mappings.

- [ ] Implement only `GET /v1/chat/thread`, `POST /v1/chat/messages`, and `DELETE /v1/chat/thread`.
- [ ] Require `get_current_user_id` on all routes.
- [ ] Reject extra request fields so clients cannot choose user/thread/provider/model.
- [ ] Reuse existing Accept-Language middleware.
- [ ] Apply per-authenticated-user rate limiting; verify keying is not IP-only for the product rule.
- [ ] Gate with `CHAT_ENABLED` plus optional beta-user allowlist.
- [ ] Map domain outcomes to the exact approved error codes/statuses.
- [ ] Add chat-specific unavailable copy; never return meal-generation-specific AI errors.
- [ ] Keep internal provider/usage/error metadata out of response schemas.
- [ ] Register the router in `src/api/main.py` only after all dependencies compose successfully.
- [ ] Update app smoke/OpenAPI tests.

**Exit criteria:** API tests prove auth, gate, ownership, schema, pagination, idempotency, busy, rate-limit, unavailable, and clear behavior.

---

## Task 8 — Observability, Privacy Guards, and Cost Controls

- [ ] Emit the approved content-free counters/histograms through `src.observability`.
- [ ] Attach only allowlisted scalar attributes.
- [ ] Measure total turn latency separately from provider latency.
- [ ] Record token usage when providers return it.
- [ ] Record context truncation/partial availability without values.
- [ ] Add product analytics events only if privacy/product review approves them; never attach content.
- [ ] Extend static logging guardrails to reject chat content/prompt/context field names in log statements.
- [ ] Add test that exception strings do not contain user text or raw provider output.
- [ ] Verify OpenTelemetry/PostHog LLM instrumentation is configured not to collect payload content.
- [ ] Add global kill switch and one-user production allowlist settings with safe defaults.
- [ ] Before cohort expansion, implement durable daily quota and cost dashboard/alert.

**Exit criteria:** a staging telemetry audit finds zero raw content and all planned metrics are visible.

---

## Task 9 — Comprehensive Verification

Run the narrow suite continuously, then the repository gates.

### Narrow tests

- [ ] `pytest tests/unit/domain/chat -q`
- [ ] `pytest tests/unit/app/chat -q`
- [ ] `pytest tests/unit/infra/chat -q`
- [ ] `pytest tests/unit/api/chat -q`
- [ ] `pytest tests/integration/infra/test_chat_repositories.py -o addopts="" -m integration -q`
- [ ] `pytest tests/integration/api/test_chat_api.py -o addopts="" -m integration -q`
- [ ] migration upgrade/downgrade/upgrade test

### Architecture and quality gates

- [ ] `lint-imports`
- [ ] `ruff check src tests`
- [ ] `black --check src tests`
- [ ] `mypy src`
- [ ] `pytest tests/unit --cov=src --cov-fail-under=65`
- [ ] confirm new chatbot critical paths have 100% branch coverage where practical and overall new-feature coverage ≥90%

### Manual staging checks

- [ ] first message and personalized response;
- [ ] process restart and history recovery;
- [ ] same-ID replay after simulated timeout;
- [ ] concurrent sends;
- [ ] provider timeout/fallback/unavailable;
- [ ] failed same-ID retry;
- [ ] clear and account delete;
- [ ] seven-language/safety prompt evaluation as approved;
- [ ] log/trace/analytics redaction audit.

**Exit criteria:** all launch gates in `operations-testing-rollout.md` pass.

---

## Task 10 — One-User Production Beta

- [ ] Deploy migration while `CHAT_ENABLED=false`.
- [ ] Deploy application code with empty allowlist.
- [ ] Verify health, router composition, and dashboards.
- [ ] Add exactly one approved internal `users.id` to the beta allowlist.
- [ ] Enable global flag.
- [ ] Run the production beta scenario checklist.
- [ ] Review daily aggregate usage, latency, provider failures, busy conflicts, stale recovery, and cost.
- [ ] Keep a documented rollback owner and command/config path.
- [ ] Disable immediately for privacy, safety, duplication, or cross-user anomaly.

**Beta exit review:** decide whether to stop, iterate prompt/context, or proceed to a small internal cohort. No automatic expansion.

---

## Task 11 — Post-Beta Readiness Before Broader Release

- [ ] Implement approved automatic retention cleanup and test it.
- [ ] Implement durable daily message/token quota.
- [ ] Complete seven-language safety and UX copy review.
- [ ] Add user-facing AI disclosure and data-retention explanation.
- [ ] Add support/incident runbook.
- [ ] Confirm provider privacy/retention configuration.
- [ ] Set and alert on daily/monthly cost budget.
- [ ] Update README, roadmap, codebase summary, system architecture, endpoint counts, and external-service docs to reflect the actual live implementation.
- [ ] Remove or correct stale historical claims that conflict with the new architecture.

Streaming, multiple threads, tools, RAG, image input, and proactive chat must each receive a separate approved design.

---

## Recommended Pull Request Slicing

1. **PR A — Domain + schema:** domain contracts, migration, ORM, repositories, UoW, PostgreSQL tests; feature still inaccessible.
2. **PR B — Vertical fake slice:** application orchestration, REST API, feature gate, fake completion adapter, full deterministic tests; disabled in production.
3. **PR C — Provider + context + operations:** managed adapter, prompt, context reader, safety eval, telemetry/redaction; staging only.
4. **PR D — One-user beta config:** dashboards/runbook, empty-by-default allowlist, production enablement procedure; no scope expansion.

Each PR must be independently reviewable and leave the service in a deployable state.

---

## Definition of Done

The implementation is done only when:

- the data and API contracts are unchanged or the design package has been updated and re-approved;
- one thread per user and one active turn per thread are database-enforced;
- idempotent replay never duplicates visible messages or provider work after a completed turn;
- provider calls hold no DB transaction/session;
- ownership and deletion are proven by integration tests;
- controlled failures leave retryable durable state;
- no raw chat or context data appears in logs/telemetry;
- safety and multilingual evals meet the approved threshold;
- repository architecture/quality/test gates pass;
- production remains disabled for everyone except the explicitly approved beta user;
- rollback has been exercised.