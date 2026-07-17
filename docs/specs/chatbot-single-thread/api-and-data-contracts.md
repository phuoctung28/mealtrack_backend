# Single-Thread Chatbot API and Data Contracts

**Status:** Proposed  
**Transport:** authenticated REST, synchronous completion  
**Source of truth:** PostgreSQL

## 1. API Surface

The client never creates or selects a thread. The server resolves the sole thread from the authenticated database user ID.

### `GET /v1/chat/thread`

Returns the latest page of the current user's conversation.

Query parameters:

| Parameter | Type | Default | Rules |
|---|---|---:|---|
| `limit` | integer | 50 | 1–100 |
| `before_sequence` | integer or null | null | Return messages with a lower sequence number |

A user with no conversation receives `200` with `thread: null` and an empty message list. GET remains side-effect free; the thread is created only by the first successful reservation in POST.

Example response:

```json
{
  "thread": {
    "id": "4b4f5a0d-7b04-4e6a-90ad-a6fc1d22d06b",
    "last_message_at": "2026-07-17T08:30:00Z"
  },
  "messages": [
    {
      "id": "9ea96d60-9dd1-4f0c-87bf-9c1471068251",
      "sequence": 1,
      "role": "user",
      "status": "completed",
      "content": "How am I doing on protein today?",
      "created_at": "2026-07-17T08:29:55Z"
    },
    {
      "id": "bf568a92-e9f8-47ac-a296-a1bad9067d8a",
      "sequence": 2,
      "role": "assistant",
      "status": "completed",
      "content": "You have logged 72 g so far against your 120 g target...",
      "created_at": "2026-07-17T08:30:00Z"
    }
  ],
  "has_more": false,
  "next_before_sequence": null
}
```

Messages are returned in ascending display order within the page. To load older history, the client sends the smallest sequence from the current page as `before_sequence`.

### `POST /v1/chat/messages`

Reserves and completes one turn. The HTTP request remains open until the assistant message is completed or a controlled error is returned.

Request:

```json
{
  "client_message_id": "8c4780bf-e062-4f2f-af02-54dc2a01828f",
  "content": "What would be a good high-protein dinner?"
}
```

Rules:

- `client_message_id` is a client-generated UUID and is required.
- `content` is trimmed, must remain non-empty, and must not exceed the configured character limit.
- Response language comes from the existing `Accept-Language` flow, then profile preference, then English.
- The request does not accept `thread_id`, `user_id`, provider, model, system prompt, or tool definitions.

Successful response (`200` for both first execution and idempotent replay):

```json
{
  "thread_id": "4b4f5a0d-7b04-4e6a-90ad-a6fc1d22d06b",
  "user_message": {
    "id": "c39f7899-d96b-4bba-8dd6-1fab34635c27",
    "sequence": 3,
    "role": "user",
    "status": "completed",
    "content": "What would be a good high-protein dinner?",
    "created_at": "2026-07-17T08:34:10Z"
  },
  "assistant_message": {
    "id": "f08fa7fd-3751-4207-a80c-1ff04ff81186",
    "sequence": 4,
    "role": "assistant",
    "status": "completed",
    "content": "A grilled chicken and lentil bowl would fit well...",
    "created_at": "2026-07-17T08:34:15Z"
  }
}
```

Provider/model/token metadata is internal and must not appear in the public message schema.

### `DELETE /v1/chat/thread`

Hard-deletes the authenticated user's thread and all messages. It is idempotent and returns `204` when no thread exists.

Deletion is rejected with `409 CHAT_TURN_IN_PROGRESS` while a non-stale generation is active. The client retries after completion or lease recovery.

## 2. Authentication and Ownership

All endpoints use `get_current_user_id`.

Ownership rules:

- The thread is resolved only by authenticated `users.id`.
- Repository methods take `user_id` even when operating on a known message/thread ID.
- Public mutation endpoints do not accept a thread identifier.
- Foreign keys cascade from `users` → `chat_threads` → `chat_messages`.
- Account deletion therefore removes chat data in the same database lifecycle as other user-owned records.

## 3. Public Message Contract

| Field | Type | Notes |
|---|---|---|
| `id` | UUID string | Server-generated |
| `sequence` | positive integer | Stable ordering within the thread |
| `role` | `user` or `assistant` | System/context/tool roles are never persisted as visible messages |
| `status` | `generating`, `completed`, or `failed` | User messages are always completed |
| `content` | string or null | Null for generating/failed assistant placeholders |
| `created_at` | RFC 3339 timestamp | UTC in transport |

A history response may contain a failed assistant row so the mobile client can render a retry affordance. It must never expose `error_detail`, provider exception text, model reasoning, prompt content, or internal context snapshots.

## 4. Persistence Model

### `chat_threads`

| Column | Type | Null | Purpose |
|---|---|---:|---|
| `id` | string UUID | no | Primary key, using repository-standard ID shape |
| `user_id` | string UUID | no | FK to `users.id`, `ON DELETE CASCADE`, unique |
| `next_sequence_no` | bigint | no | Next message sequence; starts at 1 |
| `last_message_at` | timezone-aware timestamp | yes | Latest completed/failed message activity |
| `created_at` | timezone-aware timestamp | no | Base mixin timestamp |
| `updated_at` | timezone-aware timestamp | no | Base mixin timestamp |

Constraints/indexes:

- unique constraint on `user_id`;
- index on `last_message_at` for future retention cleanup.

No title, archive flag, summary, or model configuration is stored in MVP.

### `chat_messages`

| Column | Type | Null | Purpose |
|---|---|---:|---|
| `id` | string UUID | no | Primary key |
| `thread_id` | string UUID | no | FK to `chat_threads.id`, `ON DELETE CASCADE` |
| `sequence_no` | bigint | no | Deterministic thread order |
| `role` | constrained string/enum | no | `user` or `assistant` |
| `status` | constrained string/enum | no | `generating`, `completed`, `failed` |
| `content` | text | yes | User/assistant visible content |
| `client_message_id` | string UUID | yes | Required only for user messages; idempotency key |
| `reply_to_message_id` | string UUID | yes | Assistant → user self-reference; unique |
| `prompt_version` | short string | yes | Assistant generation contract version |
| `provider` | short string | yes | Safe internal metadata |
| `model` | short string | yes | Safe internal metadata |
| `input_tokens` | integer | yes | Provider-reported usage |
| `output_tokens` | integer | yes | Provider-reported usage |
| `latency_ms` | integer | yes | Provider latency, not total request latency |
| `error_code` | short string | yes | Safe controlled code; never exception text |
| `generation_started_at` | timezone-aware timestamp | yes | Lease recovery |
| `completed_at` | timezone-aware timestamp | yes | Terminal state timestamp |
| `created_at` | timezone-aware timestamp | no | Base mixin timestamp |
| `updated_at` | timezone-aware timestamp | no | Base mixin timestamp |

Required database guarantees:

1. Unique `(thread_id, sequence_no)`.
2. Unique `(thread_id, client_message_id)` when the client ID is non-null.
3. Unique `reply_to_message_id` when non-null: one assistant placeholder/reply per user message.
4. Partial unique index on `thread_id` where `role='assistant' AND status='generating'`.
5. Role/state checks:
   - user → completed, non-empty content, client ID present, no reply target;
   - assistant/generating → null content, generation timestamp present, reply target present;
   - assistant/completed → non-empty content, completion timestamp present;
   - assistant/failed → safe error code and completion timestamp present.
6. Index `(thread_id, sequence_no DESC)` for latest-page reads.
7. Index `(status, generation_started_at)` for stale-generation inspection and future cleanup.

Domain validation repeats these invariants so errors are found before the database boundary; constraints remain the final cross-worker defense.

## 5. Message State Machine

```text
User message:       create ───────────────────────────────► completed

Assistant message:  create ► generating ► completed
                                     └──► failed ► generating (same-id retry)
```

Terminal messages are immutable through the public API. There is no individual edit/delete endpoint in MVP.

A failed retry reuses the same assistant row, `reply_to_message_id`, and sequence number. This preserves a single visual reply position and prevents duplicate turns.

## 6. Idempotency Contract

For an existing `(thread_id, client_message_id)`:

| Existing state | Incoming normalized content | Behavior |
|---|---|---|
| Completed assistant | Same | Return original pair; no provider call |
| Generating assistant | Same | Return `409 CHAT_TURN_IN_PROGRESS` with retryable metadata |
| Failed assistant | Same | Re-reserve the existing placeholder and retry |
| Any | Different | Return `409 CHAT_IDEMPOTENCY_CONFLICT` |

The server compares normalized stored content after trimming outer whitespace. It does not rewrite internal whitespace or punctuation.

## 7. Error Contract

Errors follow the repository's existing envelope:

```json
{
  "detail": {
    "error_code": "CHAT_TURN_IN_PROGRESS",
    "message": "A response is already being generated for this conversation.",
    "details": {
      "retryable": true
    }
  }
}
```

Proposed stable codes:

| HTTP | Code | Meaning |
|---:|---|---|
| 400 | `CHAT_INPUT_INVALID` | Empty/invalid/control-heavy content |
| 400 | `CHAT_INPUT_TOO_LONG` | Input exceeds configured limit |
| 403 | `CHAT_NOT_ENABLED` | Global flag or beta allowlist denies access |
| 409 | `CHAT_TURN_IN_PROGRESS` | Another non-stale turn is generating |
| 409 | `CHAT_IDEMPOTENCY_CONFLICT` | Same client ID was used for different content |
| 429 | `CHAT_RATE_LIMITED` | Burst limit exceeded |
| 429 | `CHAT_DAILY_LIMIT_REACHED` | Future durable quota exceeded |
| 503 | `CHAT_AI_UNAVAILABLE` | Timeout, rate limit, circuit breaker, or all providers unavailable |
| 503 | `CHAT_CONTEXT_UNAVAILABLE` | Only when mandatory context is configured and cannot be loaded |

The current generic AI handler uses meal-specific copy; chatbot implementation must add a chat-safe mapping rather than returning "AI meal generation is temporarily unavailable."

Unexpected failures continue to use the single global `INTERNAL_ERROR` boundary.

## 8. Chat Completion Port Contract

`ChatCompletionPort` accepts provider-neutral structured data:

- `prompt_version`;
- static system instructions;
- target response language;
- untrusted MealTrack context snapshot;
- ordered recent `user`/`assistant` history;
- current user message;
- maximum output tokens;
- timeout/deadline metadata.

It returns:

- completed visible content;
- provider and model identifiers;
- input/output token usage when available;
- provider latency;
- finish reason/truncation indicator;
- no raw SDK response object.

The application receives this DTO only. Provider errors are classified into controlled timeout, rate-limit, unavailable, invalid-output, and unknown categories.

## 9. MealTrack Context Snapshot

Proposed allowlisted shape:

```json
{
  "as_of": "2026-07-17T08:34:10Z",
  "local_date": "2026-07-17",
  "language": "en",
  "timezone": "Asia/Ho_Chi_Minh",
  "fitness_goal": "cut",
  "dietary_preferences": ["high_protein"],
  "targets": {
    "calories": 2100,
    "protein_g": 120,
    "carbs_g": 230,
    "fat_g": 65
  },
  "today": {
    "available": true,
    "consumed": {
      "calories": 1340,
      "protein_g": 72,
      "carbs_g": 151,
      "fat_g": 43
    },
    "remaining": {
      "calories": 760,
      "protein_g": 48,
      "carbs_g": 79,
      "fat_g": 22
    }
  }
}
```

All fields are optional except timestamps/availability. Missing values are omitted or null; the model is instructed not to infer them.

The snapshot must not contain names, emails, Firebase UIDs, database IDs, exact birth date, free-form medical notes, raw meal descriptions, image URLs, subscription/referral data, or notification tokens.

## 10. Prompt Contract

The static system prompt is versioned and contains:

- role and MealTrack scope;
- read-only statement;
- response-language rule;
- use of context as potentially incomplete data, never instructions;
- prohibition on claiming data was logged/edited;
- health/medical safety rules;
- concise mobile-friendly output style;
- no hidden reasoning or tool syntax;
- instruction to state uncertainty and missing-data limitations.

Dynamic data is passed separately:

1. context snapshot encoded as data;
2. recent role-preserving history;
3. current user message.

System instructions and full rendered prompts are never persisted with messages and never emitted to logs.

## 11. Configuration Contract

Proposed settings, all environment-backed:

| Setting | Beta default |
|---|---|
| `CHAT_ENABLED` | `false` |
| `CHAT_BETA_USER_IDS` | empty allowlist |
| `CHAT_MAX_INPUT_CHARS` | `4000` |
| `CHAT_HISTORY_PAGE_SIZE_MAX` | `100` |
| `CHAT_HISTORY_CONTEXT_MAX_MESSAGES` | `20` |
| `CHAT_HISTORY_CONTEXT_MAX_CHARS` | `24000` |
| `CHAT_MAX_OUTPUT_TOKENS` | `800` |
| `CHAT_AI_TIMEOUT_SECONDS` | `25` |
| `CHAT_GENERATION_LEASE_SECONDS` | `60` |
| `CHAT_RATE_LIMIT` | `10/minute` |
| `CHAT_DAILY_MESSAGE_LIMIT` | disabled for one-user beta; required before broad rollout |
| `CHAT_PROMPT_VERSION` | `chat-v1` |
| `CHAT_RETENTION_DAYS` | unset in beta; proposed `180` before broad rollout |

Model/provider selection should reuse existing text-provider configuration unless a chat-specific override is later justified. The routing purpose must still be `CHAT` for telemetry and prompt-cache separation.