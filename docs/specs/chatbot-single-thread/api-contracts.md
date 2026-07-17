# Single-Thread Chatbot API Contract

**Status:** Proposed  
**Transport:** authenticated REST with a complete synchronous response

## Ownership Rule

The server resolves the sole thread from `get_current_user_id`. Public requests never accept `user_id` or a mutable `thread_id`. Repositories still include the authenticated user ID in ownership-sensitive operations.

## `GET /v1/chat/thread`

Returns the latest history page.

| Query | Default | Rule |
|---|---:|---|
| `limit` | 50 | 1–100 |
| `before_sequence` | null | Return messages with a lower sequence number |

A user with no thread receives:

```json
{
  "thread": null,
  "messages": [],
  "has_more": false,
  "next_before_sequence": null
}
```

GET is side-effect free. The first POST creates the thread.

Messages are returned in ascending display order. `next_before_sequence` is the smallest sequence in the page when older rows exist.

## `POST /v1/chat/messages`

Request:

```json
{
  "client_message_id": "8c4780bf-e062-4f2f-af02-54dc2a01828f",
  "content": "What would be a good high-protein dinner?"
}
```

Rules:

- `client_message_id` is a required client-generated UUID.
- `content` is trimmed, non-empty, and limited by `CHAT_MAX_INPUT_CHARS`.
- Existing `Accept-Language` handling selects the response language, then profile preference, then English.
- Extra fields are rejected. Clients cannot choose a provider, model, system prompt, tool, user, or thread.

Successful response (`200` for first execution and completed idempotent replay):

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

Provider, model, token usage, prompt version, context snapshot, and internal error detail are never public fields.

## `DELETE /v1/chat/thread`

Hard-deletes the authenticated user's thread and all messages.

- Idempotent: `204` when the thread is absent.
- Rejected with `409 CHAT_TURN_IN_PROGRESS` during a non-stale generation.
- Account deletion also removes chat data through database cascades.

## Public Message Shape

| Field | Type | Notes |
|---|---|---|
| `id` | UUID string | Server-generated |
| `sequence` | positive integer | Stable per-thread order |
| `role` | `user` or `assistant` | No visible system/tool roles |
| `status` | `generating`, `completed`, or `failed` | User messages are completed |
| `content` | string or null | Null for generating/failed assistants |
| `created_at` | RFC 3339 timestamp | UTC in transport |

History may expose a failed assistant placeholder so mobile can offer retry. It must not expose exception text or provider payloads.

## Idempotency Semantics

The server scopes `client_message_id` to the user's sole thread and compares the normalized stored content.

| Existing turn | Same content | Different content |
|---|---|---|
| Assistant completed | Return original pair; no provider call | `409 CHAT_IDEMPOTENCY_CONFLICT` |
| Assistant generating | `409 CHAT_TURN_IN_PROGRESS` | `409 CHAT_IDEMPOTENCY_CONFLICT` |
| Assistant failed | Reuse the same assistant row and retry | `409 CHAT_IDEMPOTENCY_CONFLICT` |

A new client ID while another turn generates returns `409 CHAT_TURN_IN_PROGRESS`.

## Error Envelope

```json
{
  "detail": {
    "error_code": "CHAT_TURN_IN_PROGRESS",
    "message": "A response is already being generated for this conversation.",
    "details": {"retryable": true}
  }
}
```

| HTTP | Code | Meaning |
|---:|---|---|
| 400 | `CHAT_INPUT_INVALID` | Empty or invalid content |
| 400 | `CHAT_INPUT_TOO_LONG` | Input exceeds limit |
| 403 | `CHAT_NOT_ENABLED` | Flag or beta allowlist denies access |
| 409 | `CHAT_TURN_IN_PROGRESS` | Another active generation exists |
| 409 | `CHAT_IDEMPOTENCY_CONFLICT` | Client ID reused for different content |
| 429 | `CHAT_RATE_LIMITED` | Burst limit exceeded |
| 429 | `CHAT_DAILY_LIMIT_REACHED` | Future durable quota exceeded |
| 503 | `CHAT_AI_UNAVAILABLE` | Timeout, rate limit, circuit breaker, or providers unavailable |
| 503 | `CHAT_CONTEXT_UNAVAILABLE` | Only if mandatory context cannot be loaded |

Chat must not reuse the current meal-specific `AI_UNAVAILABLE` response copy. Unexpected failures remain owned by the global `INTERNAL_ERROR` boundary.