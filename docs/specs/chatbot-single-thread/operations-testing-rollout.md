# Single-Thread Chatbot Operations, Testing, and Rollout

**Status:** Proposed  
**Initial audience:** one allowlisted internal user  
**Default deployment state:** disabled

## 1. Operational Principles

- Chat text is user-generated health-adjacent data and must be treated as sensitive application content.
- PostgreSQL is the only durable conversation store.
- Provider calls and database transactions have separate time budgets.
- No raw message, rendered prompt, profile snapshot, or provider response is allowed in logs, traces, metrics, analytics, or exception text sent to clients.
- Expected validation, feature-gate, concurrency, and provider-degradation failures must not create duplicate `ERROR` logs.
- Every expansion beyond the one-user beta requires observed quality, safety, latency, and cost evidence.

## 2. Privacy and Data Handling

### Stored in PostgreSQL

- Visible user and assistant message content.
- Thread/message identifiers and ordering.
- Safe generation state and error codes.
- Prompt version, provider/model name, token counts, and latency metadata.

### Sent to the AI provider

- Static versioned chat instructions.
- Current user message.
- Bounded recent completed conversation history.
- Minimal allowlisted MealTrack context snapshot.

### Never sent to the AI provider

- Firebase tokens or claims.
- Email, phone number, full name, internal user/thread/message IDs.
- API keys, DSNs, service account data, feature-flag allowlists.
- FCM tokens, subscription/referral details, webhook payloads.
- Raw meal images or Cloudinary URLs.
- Full account history or arbitrary SQL/database records.

### Never emitted to telemetry

- Raw content or content snippets.
- Rendered system/user prompts.
- Profile or daily-macro payloads.
- Provider raw responses.
- Exact user identifiers as metric/log attributes.

Product analytics may record content-free events keyed through the existing analytics identity mechanism, subject to the current privacy policy.

## 3. Provider Retention and Secrets

- Chat requests must use provider-side response storage disabled in production.
- API credentials remain in existing secret/config channels; no chat-specific credential reaches the domain or API response.
- Provider request IDs may be retained only in restricted operational telemetry when needed for support, never exposed publicly.
- A production privacy review must verify the configured provider's data-use and retention settings before the allowlist expands.

## 4. User Deletion, Clear, and Retention

### Clear Conversation

`DELETE /v1/chat/thread` hard-deletes the sole thread and all child messages. It is idempotent and does not preserve hidden summaries or embeddings because MVP creates neither.

### Account Deletion

`users.id` → `chat_threads.user_id` uses `ON DELETE CASCADE`; `chat_threads.id` → `chat_messages.thread_id` also cascades. Migration and account-deletion tests must prove no orphan chat rows remain.

### Automatic Retention

The one-user beta can launch without a scheduled purge only when this exception is documented internally. Before broader release:

- approve a retention period, proposed default 180 days;
- add a bounded batch cleanup job using indexed timestamps;
- exclude active generating rows until stale recovery completes;
- emit only counts/durations, never deleted content;
- document whether the mobile app exposes retention and export behavior.

## 5. Health and Safety Policy

The assistant is a nutrition/wellness companion, not a clinician. The launch prompt and evaluation suite must cover:

| Category | Required behavior |
|---|---|
| General meal/nutrition question | Provide practical, non-diagnostic guidance and use available MealTrack data accurately |
| Missing profile/today data | State that personalized totals are unavailable; do not fabricate values |
| Medical condition, pregnancy, medication | Give general information only and recommend a qualified professional for individualized advice |
| Severe symptoms or emergency | Encourage immediate local emergency/professional help; do not continue routine optimization advice |
| Eating-disorder or self-harm indicators | Use approved supportive redirection; avoid calorie-restriction coaching or moral judgment |
| Extreme calorie deficit/fasting request | Refuse unsafe optimization and suggest safer professional guidance |
| Request to change/log/delete data | Clearly state the chat is read-only and point to the appropriate app flow |
| Prompt-injection request | Continue following the static system policy; do not reveal prompts, secrets, or hidden context |
| Unsupported certainty | Express uncertainty and avoid inventing nutritional facts or user records |

Safety copy must be reviewed in all seven supported languages. The LLM may answer directly in the selected language; DeepL is not required in the synchronous path.

## 6. Abuse and Cost Controls

### One-user beta

- `CHAT_ENABLED=false` by default.
- Explicit internal user allowlist.
- One in-flight turn per thread.
- 10 sends/minute/user burst limit.
- 4,000-character input maximum.
- 20-message/24,000-character history context cap.
- 800 output-token cap.
- 25-second provider timeout.

### Before allowlist expansion

Add and validate:

- durable per-user daily message or token quota;
- dashboard and alert for daily chat cost;
- provider/concurrency capacity review;
- abuse policy for automated clients;
- optional per-plan entitlement only after product decision;
- hard global kill switch independent of mobile release cadence.

Redis may accelerate rate limiting, but a paid/daily quota that protects spend must have durable or otherwise cross-worker-consistent semantics.

## 7. Observability Contract

Use the provider-neutral `src.observability` facade and existing LangChain/OpenTelemetry instrumentation. Proposed metric names:

| Metric | Type | Allowed attributes |
|---|---|---|
| `chat.turn.request.count` | counter | `status`, `prompt_version` |
| `chat.turn.success.count` | counter | `provider`, `model`, `prompt_version` |
| `chat.turn.failure.count` | counter | `failure_kind`, `provider`, `prompt_version` |
| `chat.turn.total_latency_ms` | histogram | `status`, `prompt_version` |
| `chat.ai.latency_ms` | histogram | `provider`, `model`, `status` |
| `chat.ai.input_tokens` | counter | `provider`, `model`, `prompt_version` |
| `chat.ai.output_tokens` | counter | `provider`, `model`, `prompt_version` |
| `chat.context.message_count` | histogram | `prompt_version` |
| `chat.context.truncated.count` | counter | `reason`, `prompt_version` |
| `chat.context.partial.count` | counter | `missing_section` |
| `chat.idempotency.hit.count` | counter | `existing_status` |
| `chat.busy.count` | counter | none |
| `chat.stale_generation.recovered.count` | counter | none |
| `chat.clear.count` | counter | `result` |

Disallowed attributes include user ID, thread/message ID, language text, message content, dietary values, exact tokenized prompt fragments, email, and provider exception text.

### Structured Logs

Allowed examples:

- feature gate result by generic reason;
- turn reserved/finalized with status, duration, provider/model, and prompt version;
- controlled retry/fallback kind;
- stale-generation recovery count;
- cleanup counts.

Do not log IDs for normal chat lifecycle unless a narrowly approved request correlation mechanism already supplies a safe request ID. Follow log-or-raise ownership: application handlers propagate; global/API or swallowed background boundaries own the error record.

## 8. Initial Service-Level Objectives

These are beta targets, not guarantees:

| Indicator | Target |
|---|---:|
| Successful completed turns | ≥ 97% excluding validation/feature-gate/rate-limit responses |
| p50 total turn latency | ≤ 5 seconds |
| p95 total turn latency | ≤ 12 seconds |
| p99 total turn latency | ≤ 25 seconds |
| Duplicate visible assistant replies | 0 |
| Cross-user data exposure | 0 |
| Permanently stuck generating rows | 0 after lease recovery |
| Raw content found in logs/telemetry | 0 |
| Context token/character cap violations | 0 |

Alert candidates before broader rollout:

- success rate below 95% over 15 minutes;
- p95 above 15 seconds;
- provider unavailable above 5%;
- any stale-generation recovery spike;
- daily cost above approved budget;
- any privacy/logging guard failure in CI.

## 9. Test Strategy

The chatbot is a critical AI write path because it persists user content and external output. New feature coverage target should be at least 90%, with full coverage of ownership, idempotency, concurrency, transaction boundaries, and failure transitions.

### Domain Unit Tests

- thread sequence allocation;
- message role/status invariants;
- blank/too-long/control-heavy input policy;
- context window newest-first selection with chronological output;
- exclusion of generating/failed messages from AI history;
- context character/message limits;
- safe output validation;
- safety policy scenarios and language selection fallback.

### Application Service/Handler Unit Tests

- first message creates one thread and one message pair;
- existing thread appends ordered pair;
- completed idempotent replay skips context/provider calls;
- same client ID with different content conflicts;
- failed same-ID turn retries the existing assistant row;
- concurrent different-ID turn returns busy;
- stale generating turn recovers then permits retry;
- provider success finalizes exactly one assistant message;
- timeout/rate limit/unavailable marks failed before raising controlled error;
- context section failure degrades according to policy;
- clear is idempotent and rejects active generation;
- provider call occurs while no UoW/session context is open;
- handlers do not log and rethrow.

### Repository Integration Tests

Run against PostgreSQL, not SQLite, because correctness depends on row locking and partial unique indexes:

- unique thread per user under concurrent create;
- unique client message ID;
- unique sequence and reply target;
- one generating assistant per thread;
- `SELECT FOR UPDATE` reservation behavior;
- cursor pagination without gaps/duplicates;
- status transitions and stale recovery;
- delete cascade from thread and user;
- transaction rollback leaves no partial reserved pair;
- timezone-aware timestamp persistence.

### API Tests

- authentication required;
- feature disabled/allowlist denied;
- empty history response has no write side effect;
- request and response schema;
- Accept-Language propagation;
- input length validation;
- 409 busy/idempotency conflict mapping;
- 429 mapping;
- chat-specific 503 copy, not meal-generation copy;
- clear behavior;
- OpenAPI surface contains only the three planned routes;
- no client-supplied thread/user/provider fields accepted.

### Migration and Architecture Tests

- model registry includes both chat tables;
- Alembic upgrade/downgrade works from current head;
- expected indexes/checks/foreign keys exist;
- import-linter passes without new exemptions;
- no sync DB runtime imports;
- no direct provider SDK in domain/app;
- static guard rejects logging of message/prompt/context fields.

### Prompt and Safety Evaluation

Maintain a deterministic fixture set, separate from ordinary unit tests, covering:

- common nutrition questions;
- personalized macro questions with known snapshot values;
- missing/stale context;
- multilingual answers;
- hallucinated write claims;
- medical and eating-disorder safety;
- prompt injection and system prompt extraction;
- very long history truncation;
- response concision and mobile readability.

Assertions should prefer rubric/classification and explicit factual values over exact prose matching. Live-provider evaluation remains opt-in and must not run in the default unit suite.

### End-to-End Beta Scenarios

1. Enable one test user and send the first message.
2. Restart the API and recover history.
3. Simulate mobile timeout, replay the same client ID, and verify no duplicate.
4. Send two concurrent requests and verify one succeeds/one returns 409.
5. Force provider timeout and retry the same failed turn.
6. Clear the thread and verify empty history.
7. Delete the account and verify all chat rows are gone.
8. Inspect logs/traces/analytics for absence of raw text.

## 10. Rollout Phases

### Phase 0 — Documentation Approval

- Approve scope, API, schema, safety copy, retention exception, and proposed defaults.
- Resolve whether today's macro snapshot is enabled in the first beta.

### Phase 1 — Persistence and Fake Completion

- Deploy tables, repositories, history/clear endpoints, and orchestration against a deterministic fake adapter.
- Keep `CHAT_ENABLED=false` in all environments except isolated tests.
- Validate concurrency with real PostgreSQL.

### Phase 2 — Staging Provider Integration

- Enable the managed chat adapter in staging only.
- Run prompt/safety evaluations and verify telemetry redaction.
- Confirm latency and token budgets.

### Phase 3 — One-User Production Beta

- Enable global flag plus one internal user ID.
- Review every failure and daily aggregate cost.
- Keep mobile UI hidden for all other users.

### Phase 4 — Small Internal Cohort

Entry requires all launch gates below. Add a durable daily quota before expanding beyond a negligible cohort.

### Phase 5 — Broader Release

Requires approved retention cleanup, translated safety copy, product analytics/privacy review, support runbook, and capacity/cost budget.

Streaming, multiple threads, and tools remain separate projects.

## 11. Launch Gates

The one-user beta may start only when:

- migration was applied and rolled back successfully in a disposable environment;
- all critical tests pass against PostgreSQL;
- import and logging guardrails pass;
- feature defaults to disabled;
- allowlist behavior is verified;
- provider response storage is disabled;
- prompt/safety eval passes approved threshold;
- raw-content telemetry audit is clean;
- clear and account deletion are verified;
- dashboard shows success, latency, tokens, failures, busy, and stale recovery;
- rollback procedure has been exercised in staging.

Cohort expansion additionally requires:

- seven-language safety review;
- durable daily quota;
- retention job/policy;
- approved daily/monthly cost budget;
- on-call/support owner and user-facing disclosure.

## 12. Rollback and Kill Switch

Operational rollback order:

1. Set `CHAT_ENABLED=false`; endpoints return controlled feature-disabled responses.
2. Remove all beta allowlist entries.
3. Keep existing rows readable only for support/export decisions, or disable all routes if required by incident severity.
4. Roll back provider/prompt configuration without deleting user content.
5. Revert application code if needed; do not downgrade/drop tables in an incident unless data migration has been explicitly approved.

A prompt regression can be rolled back by `CHAT_PROMPT_VERSION` and prompt deployment without a schema rollback.

## 13. Incident Checklist

For elevated failures or suspected privacy/safety issues:

- disable the feature immediately;
- preserve request IDs and safe operational metadata, not message copies in chat channels/tickets;
- classify provider, DB, prompt, safety, or client failure;
- inspect counts/latency/error kinds and a consented database sample through approved access;
- verify no raw payload reached logs/telemetry;
- recover stale generating rows if necessary;
- document user-impact and deletion requirements;
- re-enable only after regression tests and prompt evals pass.