# Single-Thread Chatbot Implementation Plan — Foundation

> Execute task-by-task. Preserve approved contracts and do not add behavior beyond the MVP.

**Goal:** authenticated, persistent, read-only chat with one thread per user and an initial one-user allowlist.

**Architecture:** FastAPI REST → CQRS handlers → `ChatOrchestrationService` → async UoW repositories, bounded MealTrack context, and `ChatCompletionPort`. PostgreSQL enforces ownership, order, idempotency, and one active generation. AI calls occur outside DB transactions.

## Scope Guardrails

- [ ] One thread per authenticated user.
- [ ] One allowlisted production beta user.
- [ ] Text-only, complete synchronous response.
- [ ] Read-only personalization; no AI tools or mutations.
- [ ] No Redis dependency for durable state/correctness.
- [ ] No new `.importlinter` exemptions.
- [ ] No raw chat data in telemetry or exception text.
- [ ] Do not claim live chat in README/roadmap before deployment.

## Planned File Map

```text
src/api/
├── routes/v1/chat.py
├── schemas/request/chat_requests.py
├── schemas/response/chat_responses.py
├── mappers/chat_mapper.py
└── dependencies/chat.py

src/app/
├── commands/chat/{send_chat_message_command,clear_chat_thread_command}.py
├── queries/chat/get_chat_thread_query.py
├── handlers/command_handlers/chat/
├── handlers/query_handlers/chat/
└── services/chat/chat_orchestration_service.py

src/domain/
├── model/chat/{chat_thread,chat_message,chat_completion}.py
├── ports/{chat_thread_repository_port,chat_message_repository_port}.py
├── ports/{chat_completion_port,chat_context_reader_port}.py
├── services/chat/{chat_context_window_policy,chat_safety_policy}.py
└── exceptions/chat_exceptions.py

src/infra/
├── database/models/{chat_thread,chat_message}.py
├── repositories/{chat_thread_repository_async,chat_message_repository_async}.py
├── services/ai/managed_chat_completion_adapter.py
├── services/ai/prompts/chat_system_prompt.py
└── adapters/chat_context_reader.py

migrations/versions/<next_revision>_add_chat_tables.py

tests/
├── unit/{api,app,domain,infra}/chat/
├── integration/api/test_chat_api.py
├── integration/infra/test_chat_repositories.py
└── migrations/test_chat_tables_migration.py
```

Expected existing-file changes:

- `src/api/main.py`
- `src/api/dependencies/event_bus.py`
- `src/api/base_dependencies.py` or smaller chat composition module
- `src/domain/model/ai/model_purpose.py`
- `src/domain/ports/async_unit_of_work_port.py`
- `src/infra/database/uow_async.py`
- `src/infra/database/models/__init__.py`
- `src/infra/config/settings.py`
- exception mapping and smoke/model-registry tests

## Task 0 — Baseline and Contract Approval

- [ ] Confirm `delivery` base and current Alembic head.
- [ ] Confirm no active chat router despite historical docs.
- [ ] Approve the three endpoints and public message schema.
- [ ] Approve feature gate and one-user allowlist semantics.
- [ ] Decide whether today's macro snapshot is enabled.
- [ ] Approve input/output/history/timeout defaults.
- [ ] Approve health, emergency, eating-disorder, and read-only copy in launch languages.
- [ ] Document beta retention exception and owner.
- [ ] Define prompt-evaluation threshold.

**Exit:** every open decision in `README.md` has an owner and answer.

## Task 1 — Domain Model, Policies, Ports, and Exceptions

- [ ] Define `ChatRole` and `ChatMessageStatus` enums.
- [ ] Define `ChatThread` with owner, next sequence, and timestamps.
- [ ] Define `ChatMessage` and allowed transitions.
- [ ] Define provider-neutral completion request/result DTOs.
- [ ] Define use-case-oriented repository ports.
- [ ] Define context-reader port and allowlisted snapshot DTO.
- [ ] Define completion port with role-preserving history and limits.
- [ ] Implement deterministic context-window policy.
- [ ] Implement input/output safety policy hooks.
- [ ] Add chat-specific exceptions and stable codes.
- [ ] Add complete domain tests before infrastructure work.

Required invariants:

- user messages are completed and non-empty;
- assistant messages have a reply target;
- completed assistants have visible content;
- failed messages store only a safe code;
- failed assistant → generating retry is allowed;
- completed messages are immutable;
- system/context/tool records are not visible messages.

**Exit:** domain tests pass with no app/API/infra dependencies.

## Task 2 — Migration and ORM Models

- [ ] Add `chat_threads` and `chat_messages` per persistence contract.
- [ ] Use timezone-aware timestamps.
- [ ] Add user → thread → message cascades.
- [ ] Add unique owner, sequence, client-ID, and reply-target constraints.
- [ ] Add partial unique index for one generating assistant/thread.
- [ ] Add history and stale-generation indexes.
- [ ] Add role/status/content checks where practical.
- [ ] Register both models in the central model registry.
- [ ] Add migration tests for tables, FKs, checks, uniques, and indexes.
- [ ] Run upgrade → one-step downgrade → upgrade on disposable PostgreSQL.

Do not add Redis state, summaries, vectors, titles, or rendered prompts.

**Exit:** reversible migration and proven account-delete cascade.

## Task 3 — Async Repositories and UoW

- [ ] Add typed chat repositories to `AsyncUnitOfWorkPort`.
- [ ] Initialize concrete repositories in `AsyncUnitOfWork`.
- [ ] Keep repositories commit-free.
- [ ] Implement get/create sole thread.
- [ ] Implement thread row lock and sequence allocation.
- [ ] Atomically reserve user plus assistant placeholder.
- [ ] Translate expected unique/index races to domain outcomes.
- [ ] Implement idempotency lookup and content conflict.
- [ ] Implement completed-pair replay.
- [ ] Implement failed-placeholder re-reservation.
- [ ] Implement assistant finalize/fail transitions with ownership checks.
- [ ] Implement lease-based stale recovery.
- [ ] Implement sequence cursor pagination.
- [ ] Implement idempotent thread delete.
- [ ] Add PostgreSQL concurrency/integration tests using separate sessions.

**Critical test:** racing workers produce one thread and one controlled loser outcome, never duplicate rows.

**Exit:** repository integration tests pass; no sync DB runtime code.

## Task 4 — Prompt and Managed AI Adapter

- [ ] Add `ModelPurpose.CHAT` without changing existing routing.
- [ ] Keep the static prompt in one versioned source.
- [ ] Preserve separate system/context/history/current-message roles.
- [ ] Mark MealTrack context as untrusted data.
- [ ] Reuse configured text model/provider by default.
- [ ] Reuse fallback/circuit-breaker only with preserved roles.
- [ ] Use chat purpose for prompt cache and telemetry.
- [ ] Disable provider response storage in production chat calls.
- [ ] Apply output and timeout limits.
- [ ] Normalize content, provider/model, usage, latency, and finish reason.
- [ ] Classify timeout, rate limit, unavailable, invalid/empty output, truncation, and unknown failures.
- [ ] Keep raw SDK/LangChain objects below infrastructure.
- [ ] Test success, fallback, timeout, empty output, usage metadata, and redaction.
- [ ] Test prompt version/static-dynamic separation/read-only/prohibited fields.

Do not concatenate history into the existing general prompt string.

**Exit:** deterministic and mocked-provider tests pass without live calls.

## Task 5 — MealTrack Context Reader

- [ ] Resolve language through request/profile/English fallback.
- [ ] Resolve timezone/local date through existing utilities.
- [ ] Read only approved goal/preferences and targets.
- [ ] Read today's consumed/remaining aggregates through existing domain behavior.
- [ ] Add `as_of` and availability flags.
- [ ] Omit absent data instead of inventing user-specific defaults.
- [ ] Exclude email, Firebase UID, IDs, raw meals/images, subscription/referral, and notification data.
- [ ] Let optional sections degrade independently.
- [ ] Test complete, partial, missing-profile, invalid-timezone, and service-failure snapshots.

**Exit:** snapshot matches allowlist and privacy tests reject prohibited fields.

Continue with [Delivery Implementation Plan](./implementation-plan-delivery.md).