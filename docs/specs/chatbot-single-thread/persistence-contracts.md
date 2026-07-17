# Single-Thread Chatbot Persistence Contract

**Status:** Proposed  
**Source of truth:** PostgreSQL/Neon through async SQLAlchemy and `AsyncUnitOfWork`

## `chat_threads`

| Column | Type | Null | Purpose |
|---|---|---:|---|
| `id` | string UUID | no | Primary key using repository-standard ID shape |
| `user_id` | string UUID | no | FK to `users.id`, `ON DELETE CASCADE`, unique |
| `next_sequence_no` | bigint | no | Next message sequence, starting at 1 |
| `last_message_at` | timezone-aware timestamp | yes | Latest terminal message activity |
| `created_at` | timezone-aware timestamp | no | Base timestamp |
| `updated_at` | timezone-aware timestamp | no | Base timestamp |

Required constraints/indexes:

- unique `user_id`: at most one thread per user;
- index `last_message_at` for future retention cleanup.

MVP does not store title, archive state, summary, embedding, provider preference, or model preference.

## `chat_messages`

| Column | Type | Null | Purpose |
|---|---|---:|---|
| `id` | string UUID | no | Primary key |
| `thread_id` | string UUID | no | FK to `chat_threads.id`, `ON DELETE CASCADE` |
| `sequence_no` | bigint | no | Stable order inside the thread |
| `role` | constrained string/enum | no | `user` or `assistant` |
| `status` | constrained string/enum | no | `generating`, `completed`, `failed` |
| `content` | text | yes | Visible text |
| `client_message_id` | string UUID | yes | Required for user messages; idempotency key |
| `reply_to_message_id` | string UUID | yes | Assistant → user self-reference |
| `prompt_version` | short string | yes | Version used for assistant generation |
| `provider` | short string | yes | Safe internal metadata |
| `model` | short string | yes | Safe internal metadata |
| `input_tokens` | integer | yes | Provider-reported usage |
| `output_tokens` | integer | yes | Provider-reported usage |
| `latency_ms` | integer | yes | Provider latency only |
| `error_code` | short string | yes | Controlled code; never raw exception text |
| `generation_started_at` | timezone-aware timestamp | yes | Lease recovery |
| `completed_at` | timezone-aware timestamp | yes | Terminal-state timestamp |
| `created_at` | timezone-aware timestamp | no | Base timestamp |
| `updated_at` | timezone-aware timestamp | no | Base timestamp |

## Database Guarantees

1. Unique `(thread_id, sequence_no)`.
2. Unique `(thread_id, client_message_id)` when the client ID is non-null.
3. Unique `reply_to_message_id` when non-null: one assistant placeholder/reply per user message.
4. PostgreSQL partial unique index on `thread_id` where `role='assistant' AND status='generating'`.
5. Index `(thread_id, sequence_no DESC)` for latest-page reads.
6. Index `(status, generation_started_at)` for stale generation recovery and future cleanup.
7. Cascades `users` → `chat_threads` → `chat_messages`.
8. Role/state checks where practical:
   - user: completed, non-empty content, client ID present, no reply target;
   - assistant/generating: null content, reply target and start time present;
   - assistant/completed: non-empty content and completion time present;
   - assistant/failed: safe error code and completion time present.

Domain validation duplicates these invariants for early errors; database constraints remain the final multi-worker defense.

## Message State Machine

```text
User:       create ───────────────────────────────► completed

Assistant:  create ► generating ► completed
                         └───────► failed ► generating (same-ID retry)
```

- Completed messages are immutable through MVP APIs.
- A failed retry reuses the same assistant row, reply target, and sequence number.
- System instructions, context snapshots, and provider errors are not visible message rows.
- There is no per-message edit/delete endpoint.

## Reservation Transaction

A send begins with one short transaction:

1. Load or create the user's thread.
2. Lock the thread row.
3. Recover an expired generating lease if present.
4. Resolve `client_message_id` idempotency.
5. Reject a different active turn.
6. Allocate two sequence numbers.
7. Insert the completed user message.
8. Insert the assistant placeholder in `generating` state.
9. Advance `next_sequence_no` and commit.

The AI provider is not called until this transaction is closed.

## Completion Transaction

After provider success, a new UoW updates the reserved assistant row to `completed` and stores visible content plus safe provider/usage metadata.

After a controlled provider failure, a new UoW updates the same row to `failed` with a safe code. The client may retry the same `client_message_id`; no second assistant row is created.

If final persistence fails after provider success, the application may retry the DB write once with the same row ID. A later client retry can repeat provider work, but constraints still prevent duplicate visible messages.

## Concurrency Contract

Correctness does not rely on an in-process lock.

- Thread row lock serializes sequence allocation.
- The partial unique index blocks two active assistant generations even across workers.
- Unique client ID blocks duplicate mobile retries.
- Unique reply target blocks duplicate assistant rows.
- Expected constraint races are translated into domain outcomes, not leaked as raw `IntegrityError`.

A different message sent while one response is generating returns `CHAT_TURN_IN_PROGRESS` instead of waiting for the provider call.

## Stale Generation Recovery

`generation_started_at` acts as a lease.

- A generating assistant older than `CHAT_GENERATION_LEASE_SECONDS` is moved to `failed` with `CHAT_GENERATION_STALE`.
- Recovery may run during the next send or history read.
- The one-user beta needs no background sweeper.
- Broader retention/cleanup jobs use the stale-generation index and must not remove a genuinely active row.

## Pagination Contract

History uses sequence-based keyset pagination.

- Latest page: highest `sequence_no`, returned ascending for display.
- Older page: `sequence_no < before_sequence`.
- Cursor reads must not duplicate or skip rows when new messages arrive.
- Provider/internal metadata stays excluded from repository-to-API mapping.

## Delete Contract

- `DELETE /v1/chat/thread` hard-deletes thread and child messages.
- Deleting a user cascades through both tables.
- Delete is idempotent when no thread exists.
- Delete is rejected during a non-stale active generation.
- Migration/integration tests must prove no orphan rows remain.

## Migration Requirements

- Generate the next revision from the current Alembic head; do not assume a fixed number in advance.
- Import both ORM models in the centralized model registry.
- Test upgrade, one-step downgrade, and re-upgrade against PostgreSQL.
- Inspect partial indexes, checks, FKs, and timezone-aware columns in migration tests.
- Do not use Redis or create a third chat table for the MVP.