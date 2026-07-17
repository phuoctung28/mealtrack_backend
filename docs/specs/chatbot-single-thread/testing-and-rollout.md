# Single-Thread Chatbot Testing and Rollout

**Status:** Proposed  
**Coverage target:** ≥90% for the new feature; full coverage of critical correctness paths

## Test Strategy

The chatbot is an AI-backed write path because it persists user input and external output. Ownership, idempotency, concurrency, transaction boundaries, and failure transitions are critical paths.

### Domain Unit Tests

- thread sequence allocation;
- role/status invariants;
- blank, too-long, and control-heavy input;
- newest bounded history selection with chronological output;
- exclusion of generating/failed messages from model history;
- message/character context caps;
- safe output validation;
- safety scenarios and language fallback.

### Application Service and Handler Tests

- first message creates one thread and one message pair;
- existing thread appends an ordered pair;
- completed same-ID replay skips context/provider calls;
- same client ID with different content conflicts;
- failed same-ID turn retries the existing assistant row;
- concurrent different-ID turn returns busy;
- stale generation recovers before retry;
- provider success finalizes exactly one assistant row;
- timeout/rate limit/unavailable marks failed before raising a controlled error;
- optional context failure degrades according to policy;
- clear is idempotent and rejects active generation;
- provider call occurs with no open UoW/session;
- handlers do not log and rethrow.

### PostgreSQL Repository Integration Tests

SQLite is insufficient because correctness depends on row locking and partial unique indexes.

- unique thread per user under concurrent create;
- unique client message ID;
- unique sequence and reply target;
- one generating assistant per thread;
- `SELECT FOR UPDATE` reservation behavior;
- cursor pagination without gaps/duplicates;
- status transitions and stale recovery;
- thread/user delete cascades;
- rollback leaves no partial reserved pair;
- timezone-aware timestamps.

### API Tests

- authentication required;
- feature disabled and allowlist denied;
- empty history query has no write side effect;
- exact request/response schema;
- Accept-Language propagation;
- input limit validation;
- 409 busy and idempotency conflict mapping;
- 429 mapping;
- chat-specific 503 copy, not meal-generation copy;
- clear behavior;
- OpenAPI includes only the three approved routes;
- client-supplied user/thread/provider/model fields are rejected.

### Migration and Architecture Tests

- model registry includes both chat tables;
- Alembic upgrade/downgrade from current head;
- expected indexes, checks, and FKs;
- import-linter passes without new exemptions;
- no sync DB runtime imports;
- no provider SDK import in domain/app;
- logging guard rejects message/prompt/context values.

### Prompt and Safety Evaluation

Maintain deterministic fixtures for:

- common nutrition questions;
- personalized macro questions with known snapshot values;
- missing/stale context;
- multilingual answers;
- hallucinated write claims;
- medical and eating-disorder safety;
- prompt injection/system prompt extraction;
- long-history truncation;
- response concision and mobile readability.

Prefer rubric/classification and explicit factual assertions over exact prose matching. Live-provider evaluation is opt-in and excluded from the default unit suite.

## End-to-End Beta Scenarios

1. Enable one test user and send the first message.
2. Restart the API and recover history.
3. Simulate mobile timeout, replay the same client ID, and verify no duplicate.
4. Send two concurrent requests and verify one succeeds and one returns 409.
5. Force provider timeout and retry the same failed turn.
6. Clear the thread and verify empty history.
7. Delete the account and verify all chat rows are gone.
8. Inspect logs, traces, and analytics for absence of raw text.

## Rollout Phases

### Phase 0 — Documentation Approval

- Approve scope, API, schema, safety copy, retention exception, and defaults.
- Decide whether today's macro snapshot is enabled in beta.

### Phase 1 — Persistence and Fake Completion

- Deploy tables, repositories, history/clear endpoints, and orchestration against a deterministic fake adapter.
- Keep `CHAT_ENABLED=false` outside isolated tests.
- Validate concurrency against real PostgreSQL.

### Phase 2 — Staging Provider Integration

- Enable the managed chat adapter in staging only.
- Run prompt/safety evaluation and telemetry redaction audit.
- Confirm latency and token budgets.

### Phase 3 — One-User Production Beta

- Enable global flag plus one internal user ID.
- Review every failure and daily aggregate cost.
- Keep mobile UI hidden for all other users.

### Phase 4 — Small Internal Cohort

Requires all launch gates and a durable daily quota before expansion beyond a negligible cohort.

### Phase 5 — Broader Release

Requires retention cleanup, translated safety copy, privacy/product analytics review, support runbook, and capacity/cost budget.

Streaming, multiple threads, tools, RAG, and attachments remain separate projects.

## One-User Beta Launch Gates

- Migration applied and rolled back in a disposable environment.
- Critical tests pass against PostgreSQL.
- Import and logging guardrails pass.
- Feature defaults to disabled.
- Allowlist behavior verified.
- Provider response storage disabled.
- Prompt/safety evaluation meets approved threshold.
- Raw-content telemetry audit is clean.
- Clear and account deletion verified.
- Dashboard shows success, latency, tokens, failures, busy, and stale recovery.
- Rollback exercised in staging.

## Cohort-Expansion Gates

- Seven-language safety review.
- Durable daily quota.
- Approved retention job and policy.
- Approved daily/monthly cost budget.
- On-call/support owner.
- User-facing AI and data-retention disclosure.

## Rollback and Kill Switch

Operational rollback order:

1. Set `CHAT_ENABLED=false`.
2. Remove beta allowlist entries.
3. Preserve existing rows unless an approved deletion/export decision says otherwise.
4. Roll back prompt/model/provider configuration independently of schema.
5. Revert application code if needed; do not drop tables during an incident without an approved data plan.

A prompt regression should be rolled back through `CHAT_PROMPT_VERSION` rather than a database rollback.

## Incident Checklist

For elevated failure or suspected privacy/safety issues:

- disable the feature;
- preserve safe request IDs and aggregate metadata, not message copies in tickets/chat;
- classify provider, DB, prompt, safety, or client failure;
- inspect counts, latency, and error kinds;
- access message content only through approved, consented operational procedures;
- verify no raw payload reached telemetry;
- recover stale generations if needed;
- document user impact and deletion obligations;
- re-enable only after regression tests and prompt evaluations pass.