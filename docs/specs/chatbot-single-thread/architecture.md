# Single-Thread Chatbot Architecture

**Status:** Proposed  
**Related:** [Overview](./README.md) · [Contracts](./api-and-data-contracts.md) · [Delivery Plan](./implementation-plan.md)

## 1. Architectural Intent

Chatbot becomes a small bounded context that fits MealTrack's existing four-layer architecture:

```text
Mobile client
    │ authenticated REST
    ▼
FastAPI chat router
    │ commands / queries
    ▼
Chat application handlers + ChatOrchestrationService
    ├── Chat repositories through AsyncUnitOfWorkPort
    ├── ChatContextReaderPort
    ├── ChatCompletionPort
    └── ChatSafetyPolicy / ChatContextWindowPolicy
            │
            ▼
PostgreSQL repositories + managed AI adapter + existing MealTrack read models
```

The API process remains stateless. PostgreSQL owns all durable chat state and cross-worker concurrency rules. Redis may support optional rate limiting later, but chat correctness cannot depend on Redis being available.

## 2. Guiding Principles

1. **One user, one server-owned thread.** Clients never choose a mutable thread ID.
2. **Short database transactions.** No DB connection remains checked out during provider latency.
3. **Database-backed correctness.** Idempotency and concurrency have unique constraints, not only in-memory locks.
4. **Read-only AI.** The model receives bounded data and returns text; it cannot call application commands.
5. **Structured conversation roles.** System instructions, context data, history, and the current user message remain distinct.
6. **Privacy by minimization.** Only fields needed for the answer enter the prompt; raw identifiers and full records do not.
7. **Graceful degradation.** Missing personalization should not make ordinary chat unavailable.
8. **No new layer debt.** New app/domain modules must not require additions to `.importlinter` ignore lists.

## 3. Proposed Components by Layer

### API Layer

| Component | Responsibility |
|---|---|
| `src/api/routes/v1/chat.py` | Authenticated GET/POST/DELETE endpoints; rate-limit decorators; no business logic |
| `src/api/schemas/request/chat_requests.py` | Input content and `client_message_id` validation |
| `src/api/schemas/response/chat_responses.py` | Stable thread/message/page contracts |
| `src/api/mappers/chat_mapper.py` | Domain-to-API mapping, including failed/generating status |
| Chat feature dependency | Global enable flag and optional beta-user allowlist |

The route uses `get_current_user_id`; it never accepts `user_id` or `thread_id` from the request body.

### Application Layer

| Component | Responsibility |
|---|---|
| `SendChatMessageCommand` | Write use case for one complete user/assistant turn |
| `ClearChatThreadCommand` | Idempotent deletion of the current user's thread |
| `GetChatThreadQuery` | Read-only cursor-paginated history |
| `ChatOrchestrationService` | Reserve, load context, call AI, finalize or fail the assistant message |
| Command/query handlers | Thin adapters around the service and UoW factory |

The orchestration service depends on domain ports and a UoW factory. It must not import SQLAlchemy, provider SDKs, FastAPI, or infrastructure settings.

### Domain Layer

| Component | Responsibility |
|---|---|
| `ChatThread` | User ownership and next sequence allocation |
| `ChatMessage` | Role/status invariants and safe state transitions |
| `ChatCompletionRequest/Result` | Provider-neutral conversational contract |
| `ChatThreadRepositoryPort` | Get/create/lock/delete the user's sole thread |
| `ChatMessageRepositoryPort` | Reserve turn, read history, finalize/fail/recover |
| `ChatCompletionPort` | Structured chat completion boundary |
| `ChatContextReaderPort` | Minimal MealTrack snapshot for personalization |
| `ChatContextWindowPolicy` | Deterministic bounded history selection |
| `ChatSafetyPolicy` | Input/output policy decisions independent of provider SDKs |

### Infrastructure Layer

| Component | Responsibility |
|---|---|
| Async chat repositories | SQLAlchemy persistence, row locking, cursor reads, constraints |
| Chat ORM models | `chat_threads` and `chat_messages` mappings |
| Managed chat completion adapter | Structured provider messages, purpose routing, timeout, fallback, usage metadata |
| MealTrack context reader | Reads profile/targets/today aggregates through existing repositories/services |
| Alembic migration | Tables, indexes, checks, foreign keys, and downgrade |
| Composition root updates | UoW repositories, event-bus registrations, router dependency wiring |

## 4. Turn Lifecycle

A turn is synchronous from the client's perspective but uses three short persistence phases.

```text
Client                 API / App                 PostgreSQL                 AI provider
  │ POST message           │                         │                           │
  ├───────────────────────►│ authenticate + validate │                           │
  │                        ├── reserve transaction ─►│ lock/get thread           │
  │                        │                         │ insert user message        │
  │                        │                         │ insert assistant:generating│
  │                        │◄──── commit / close ────┤                           │
  │                        ├── context read txn ────►│ history + user snapshot   │
  │                        │◄──── close ─────────────┤                           │
  │                        ├────────────────────────────────────────────────────►│
  │                        │                         │                  completion│
  │                        │◄────────────────────────────────────────────────────┤
  │                        ├── finalize txn ────────►│ assistant:completed       │
  │                        │◄──── commit / close ────┤                           │
  │◄───────────────────────┤ response pair            │                           │
```

### Phase A — Reserve

Within one transaction:

1. Load or create the user's thread.
2. Lock the thread row while allocating sequence numbers.
3. Resolve `client_message_id` idempotency.
4. Reject a different request when an assistant message is already generating.
5. Persist the completed user message.
6. Persist an empty assistant placeholder in `generating` state.
7. Commit before any AI or external call.

### Phase B — Build Context and Generate

After the reserve transaction closes:

1. Load the recent completed conversation window.
2. Load a minimal MealTrack snapshot in a separate short read transaction.
3. Apply safety and context-window policy.
4. Call `ChatCompletionPort` with structured roles.
5. Validate non-empty, bounded output.

The provider call is never wrapped in a UoW context.

### Phase C — Finalize

Within a new transaction:

- success: update the reserved assistant row to `completed`, store content plus safe operational metadata, and update `last_message_at`;
- controlled failure: update the same row to `failed` with a safe error code and completion timestamp;
- never create a second assistant row for the same user message.

If final persistence fails after a successful provider response, retry the DB write locally with a bounded attempt. A later client retry may incur another provider call, but database constraints still prevent duplicate visible messages.

## 5. Concurrency and Ordering

The design uses defense in depth:

- `chat_threads.user_id` is unique: one thread per user.
- The reservation transaction locks the thread row.
- Each thread owns a monotonically increasing `next_sequence_no`.
- `(thread_id, sequence_no)` is unique.
- `(thread_id, client_message_id)` is unique for user messages.
- `reply_to_message_id` is unique for assistant messages.
- A PostgreSQL partial unique index permits only one `assistant/generating` row per thread.

Two app workers receiving simultaneous sends therefore cannot both reserve a turn. The loser receives a stable `CHAT_TURN_IN_PROGRESS` conflict rather than waiting behind an unbounded provider call.

A generating row carries `generation_started_at`. On the next send or history read, a row older than the configured lease is changed to `failed/CHAT_GENERATION_STALE`. The beta does not require a background sweeper.

## 6. Idempotency Model

The mobile client generates a UUID `client_message_id` for each user intent and reuses it after network timeout.

- Existing completed turn: return the original pair without an AI call.
- Existing generating turn: return conflict/pending state; do not create a duplicate.
- Existing failed turn with the same ID: atomically move the existing assistant placeholder back to `generating` and retry.
- New ID while another turn generates: return `409 CHAT_TURN_IN_PROGRESS`.

Idempotency is scoped to the server-owned thread. A client cannot replay an ID into another user's history.

## 7. Context Assembly

The MVP does not expose general database tools to the model. `ChatContextReaderPort` returns one allowlisted snapshot:

- response language;
- user's timezone and local date;
- fitness goal and dietary preferences;
- configured calorie/macro targets;
- today's aggregate consumed and remaining macros;
- an `as_of` timestamp and per-section availability flags.

It excludes email, Firebase claims, internal IDs, raw meal rows, image URLs, referral/subscription data, notification tokens, free-form profile fields, and provider credentials.

Context reads should run in parallel where safe and degrade independently. If today's aggregate fails, the assistant can still answer from conversation history, but the prompt explicitly marks current totals as unavailable so the model does not invent them.

The context window contains only completed user/assistant messages. Failed placeholders, system prompts, provider errors, and hidden metadata are never sent back to the model.

## 8. Prompt and Provider Architecture

A dedicated `ChatCompletionPort` avoids forcing conversational traffic through the current flattened `generate(prompt, system_message)` contract.

The request contains:

1. versioned static system instructions;
2. a separately encoded, untrusted MealTrack context data block;
3. recent role-preserving history;
4. the current user message;
5. output and timeout limits.

The managed adapter should reuse the repository's purpose-based routing, circuit-breaker, prompt-cache, provider timeout, and usage-extraction patterns. Add a distinct `ModelPurpose.CHAT` so chat can be configured and measured independently of `GENERAL`.

The static system prompt remains stable for provider-side prompt caching. Dynamic profile/history data never participates in cache keys and is never logged.

The model returns plain text or a product-approved limited Markdown subset. It returns no hidden reasoning, tool call, SQL, command object, or provider payload.

## 9. Safety Boundary

Safety is layered rather than delegated entirely to the model:

- API validation rejects blank, control-character-heavy, or over-limit input.
- `ChatSafetyPolicy` identifies unsupported requests and supplies deterministic response guidance.
- The system prompt prohibits diagnosis, medication/treatment instructions, unsafe extreme restriction, and claims that data was changed.
- The output validator rejects empty or oversized provider output.
- The UI must label responses as AI-generated and provide product-approved health guidance copy.
- Serious symptoms, emergencies, self-harm, or eating-disorder risk receive safe redirection, not individualized clinical advice.

Because MVP has no tools and receives no secrets, prompt injection cannot cause a write or credential disclosure. It can still affect response quality, so context is encoded as untrusted data and user content never enters system instructions.

## 10. Failure and Recovery Semantics

| Failure | Durable state | API behavior |
|---|---|---|
| Validation or feature gate | No message rows | 4xx with stable code |
| DB reserve failure | No provider call | Existing global exception handling |
| Concurrent turn | Existing generating row unchanged | 409, retryable |
| Context snapshot partial failure | Turn continues with availability flags | 200 if provider succeeds |
| Provider timeout/rate limit/all providers down | Assistant row becomes failed | 503 or timeout mapping, retryable |
| Empty/invalid provider output | Assistant row becomes failed | Controlled chat generation error |
| Process crash during generation | Assistant remains generating until lease recovery | Next request marks stale and permits retry |
| User/account deleted mid-turn | Cascade removes thread/messages | Finalization aborts; no orphan data |
| Clear requested during generation | No deletion | 409 until turn finishes or lease expires |

Handlers follow the repository's log-or-raise rule. Request handlers do not log and rethrow; the global boundary owns unexpected errors. Controlled AI degradation uses warning-level operational signals.

## 11. Scaling Properties

The MVP architecture is intentionally multi-worker safe even though rollout begins with one user:

- no process-local conversation state;
- no WebSocket connection registry;
- database constraints serialize per-thread turns;
- provider work occurs without holding a DB pool slot;
- history and context are bounded;
- indexes support latest-page retrieval and future retention cleanup;
- rate limits and output tokens cap cost per request.

The first likely bottleneck is provider latency/cost, not chat persistence. Broader rollout should add a durable daily usage ledger or equivalent quota control before increasing the allowlist substantially.

## 12. Rejected MVP Alternatives

| Alternative | Reason rejected now |
|---|---|
| WebSocket-first transport | Connection lifecycle, auth refresh, ordering, reconnect recovery, and multi-worker fan-out are unnecessary for a complete-response MVP |
| Redis conversation store | Optional/transient infrastructure; risks lost history and split truth |
| Messages table without a thread table | Makes one-thread invariant, sequence allocation, locking, clear, and future multi-thread migration harder |
| Reusing `ModelPurpose.GENERAL` with concatenated history | Loses role boundaries and weakens prompt-injection isolation and feature-level telemetry |
| LLM tool calling | Requires authorization, confirmation, audit, rollback, and per-tool safety design |
| Holding one UoW during AI generation | Consumes a pooled DB connection and increases rollback/timeout risk |
| Automatic summary/RAG at launch | Adds extra calls, evaluation burden, privacy surface, and failure modes before basic chat is proven |

## 13. Evolution Path

The design supports later additions without changing the MVP contract abruptly:

1. Add SSE streaming while keeping the same reservation/finalization rows.
2. Add automatic summaries when the bounded history window becomes insufficient.
3. Add multiple threads by removing the unique user constraint and introducing explicit thread routes.
4. Add read-only tools with a strict registry and per-tool authorization.
5. Add write tools only with explicit confirmation and domain commands.
6. Add image messages and multimodal providers with separate attachment storage.

Each expansion requires a new design review; none is implicit in the first implementation.