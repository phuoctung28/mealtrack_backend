# Single-Thread Chatbot Operations and Safety

**Status:** Proposed  
**Initial audience:** one allowlisted internal user  
**Default deployment state:** disabled

## Operational Principles

- Treat chat text as sensitive health-adjacent application content.
- PostgreSQL is the only durable conversation store.
- Give database transactions and provider calls separate time budgets.
- Never emit raw messages, rendered prompts, profile snapshots, or provider responses to logs, traces, metrics, analytics, or client errors.
- Validation, feature-gate, concurrency, and provider-degradation outcomes must not create duplicate `ERROR` logs.
- Expand beyond one user only after observed quality, safety, latency, and cost evidence.

## Privacy and Data Handling

### Stored in PostgreSQL

- Visible user and assistant message content.
- Thread/message identifiers and ordering.
- Safe status and error codes.
- Prompt version, provider/model name, token counts, and latency metadata.

### Sent to the AI provider

- Static versioned instructions.
- Current user message.
- Bounded recent completed history.
- Minimal allowlisted MealTrack context snapshot.

### Never sent to the AI provider

- Firebase tokens or claims.
- Email, phone, full name, or internal IDs.
- API keys, DSNs, service-account data, or allowlists.
- FCM tokens, subscription/referral data, or webhook payloads.
- Raw meal images, image URLs, or arbitrary database records.

### Never emitted to telemetry

- Raw content or snippets.
- Rendered system/user prompts.
- Profile or daily-macro payloads.
- Provider raw responses.
- Exact user/thread/message identifiers as metric/log attributes.

Content-free product events may use the existing analytics identity mechanism only after privacy/product review.

## Provider Retention and Secrets

- Disable provider-side response storage for production chat requests.
- Keep credentials in existing secret/config channels.
- Retain provider request IDs only in restricted operational telemetry when support requires them.
- Verify provider data-use and retention configuration before expanding the allowlist.

## Deletion and Retention

### Clear Conversation

`DELETE /v1/chat/thread` hard-deletes the sole thread and child messages. MVP creates no hidden summary, embedding, or secondary chat store.

### Account Deletion

Database cascades remove `chat_threads` and `chat_messages`. Migration and integration tests must prove there are no orphan rows.

### Automatic Retention

The one-user beta may temporarily launch without scheduled purge only with a documented exception. Before broader release:

- approve a retention period, proposed default 180 days;
- add bounded indexed cleanup batches;
- exclude active generations until stale recovery finishes;
- emit counts/durations only;
- decide whether the client exposes retention and export behavior.

## Health and Safety Policy

The assistant is a nutrition/wellness companion, not a clinician.

| Category | Required behavior |
|---|---|
| General nutrition question | Practical, non-diagnostic guidance using available data accurately |
| Missing user/today data | State the limitation; do not fabricate totals |
| Medical condition, pregnancy, medication | General information only; recommend qualified individualized advice |
| Severe symptoms or emergency | Encourage immediate local emergency/professional help |
| Eating-disorder or self-harm indicators | Approved supportive redirection; no restriction coaching or moral judgment |
| Extreme deficit/fasting request | Decline unsafe optimization and suggest safer professional guidance |
| Request to change/log/delete data | State that chat is read-only and point to the correct app flow |
| Prompt injection | Keep static policy; do not reveal prompts, secrets, or hidden context |
| Unsupported certainty | Express uncertainty and avoid inventing nutritional facts or user records |

Safety copy requires review in all supported launch languages. The LLM may answer directly in the selected language; DeepL is not required in the synchronous path.

## Abuse and Cost Controls

### One-user beta defaults

- `CHAT_ENABLED=false`.
- Explicit internal user allowlist.
- One in-flight turn per thread.
- 10 sends/minute/user.
- 4,000 input characters.
- 20 messages / 24,000 history characters.
- 800 output tokens.
- 25-second provider timeout.

### Before allowlist expansion

- Durable per-user daily message or token quota.
- Daily cost dashboard and alert.
- Provider/concurrency capacity review.
- Abuse policy for automated clients.
- Optional plan entitlement only after a product decision.
- Hard global kill switch independent of mobile release cadence.

Redis may accelerate burst limits, but spend-protection quotas must be cross-worker consistent and preferably durable.

## Observability Contract

Use the provider-neutral `src.observability` facade and existing LangChain/OpenTelemetry instrumentation.

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

Disallow user IDs, message/thread IDs, message text, dietary values, prompt fragments, email, and provider exception text as attributes.

### Structured Logs

Allowed signals:

- generic feature-gate reason;
- turn reserved/finalized status and duration;
- provider/model/prompt version;
- controlled retry/fallback kind;
- stale recovery and cleanup counts.

Do not log normal lifecycle IDs unless an approved request-correlation mechanism already supplies a safe request ID. Follow log-or-raise ownership: handlers propagate; global or swallowed boundaries own errors.

## Initial SLOs

| Indicator | Beta target |
|---|---:|
| Successful completed turns | ≥ 97% excluding validation/gate/rate-limit |
| p50 total latency | ≤ 5 seconds |
| p95 total latency | ≤ 12 seconds |
| p99 total latency | ≤ 25 seconds |
| Duplicate visible assistant replies | 0 |
| Cross-user data exposure | 0 |
| Permanently stuck generating rows | 0 after lease recovery |
| Raw content in telemetry | 0 |
| Context cap violations | 0 |

Alert candidates before broader rollout:

- success below 95% over 15 minutes;
- p95 above 15 seconds;
- provider unavailable above 5%;
- stale-recovery spike;
- daily cost above budget;
- any privacy/logging guard failure in CI.