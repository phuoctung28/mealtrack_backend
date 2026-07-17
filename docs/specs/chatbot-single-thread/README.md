# Single-Thread MealTrack Chatbot — Design Package

**Date:** 2026-07-17  
**Status:** Proposed — documentation only  
**Initial rollout:** one allowlisted beta user  
**Product invariant:** each authenticated MealTrack user owns at most one persistent chat thread

## Executive Summary

This package defines the first production-shaped chatbot slice for MealTrack without implementing it.

The proposed MVP is deliberately narrow:

- one persistent thread per authenticated user;
- one in-flight turn per thread;
- authenticated REST, with a complete JSON response rather than WebSocket/SSE streaming;
- PostgreSQL as the durable source of truth;
- read-only personalization from a bounded MealTrack context snapshot;
- no LLM tools, no meal/profile mutations, no images, and no background agent work;
- existing provider routing, prompt-cache, observability, and exception conventions reused where appropriate;
- deployment disabled by default and initially allowlisted to one internal user.

The one-user beta is a rollout restriction, not a database shortcut. The schema and ownership rules remain correct for many users, while every user is constrained to exactly one logical thread.

## Current-State Audit

The current repository is ready to host the feature, but the active runtime does not contain a chatbot route:

- `src/api/main.py` registers the live v1 routers but no chat router.
- `src/domain/model/ai/model_purpose.py` has no dedicated chat purpose.
- `AIProviderPort.generate()` accepts a flattened prompt rather than structured conversation messages.
- `AsyncUnitOfWork` and the database model registry contain no chat repositories or tables.
- README/roadmap references to a historical real-time chat implementation should be treated as stale until a live route and persistence path exist.

This design therefore treats chatbot as a new bounded context, not as a small patch to an active chat subsystem.

## Goals

1. Give a signed-in user a durable MealTrack nutrition assistant conversation.
2. Preserve strict user ownership and deterministic message ordering.
3. Make mobile retries safe through idempotency.
4. Avoid holding a database transaction while waiting for an AI provider.
5. Personalize answers without exposing raw identifiers or arbitrary database access to the model.
6. Follow the repository's Clean Architecture, CQRS, async SQLAlchemy, logging, and test guardrails.
7. Keep the first rollout reversible through a feature flag and one-user allowlist.

## Non-Goals for the First Slice

- Multiple threads, thread titles, search, sharing, or collaborative chat.
- WebSocket or SSE token streaming.
- Voice, image, file, or barcode messages.
- LLM tool calling or any AI-initiated data mutation.
- Meal logging, profile edits, macro changes, or notification scheduling from chat.
- Vector memory, embeddings, RAG, or automatic long-term summaries.
- Proactive/background messages.
- Medical diagnosis, treatment, medication advice, or emergency triage beyond safe redirection.
- Subscription/paywall design.

## Core Decisions

| Concern | MVP decision | Reason |
|---|---|---|
| Thread ownership | One `chat_threads` row per `users.id`, enforced by a unique constraint | Matches product scope and prevents IDOR-prone client thread selection |
| Beta scope | Global flag plus one-user allowlist | Small operational blast radius without corrupting the domain model |
| Transport | REST, non-streaming | Lowest complexity; stateless across workers; no connection manager or sticky sessions |
| Persistence | PostgreSQL/Neon | Redis is optional in this codebase and must not own durable conversation state |
| Ordering | Per-thread sequence numbers | Stable history pagination and deterministic turn order |
| Concurrency | One generating assistant message per thread | Prevents crossed replies and context races |
| Retry model | Client-provided `client_message_id` with server idempotency | Safe mobile retry after timeout or reconnect |
| Personalization | Allowlisted read-only snapshot: language, timezone, goal/preferences, targets, today's aggregate macros | Useful context with bounded privacy and token cost |
| AI boundary | Dedicated `ChatCompletionPort` using structured roles | Avoids flattening system/history/user content into one injection-prone string |
| Writes from AI | Forbidden | Removes tool authorization, confirmation, rollback, and audit complexity from MVP |
| History sent to model | Recent bounded window only | Controls cost and context size; full history remains available to the user |
| Rollout | Disabled by default; one internal user; staged expansion | Easy rollback and evidence-based tuning |

## Documentation Map

- [Architecture](./architecture.md) — components, layer boundaries, turn lifecycle, concurrency, context assembly, and evolution path.
- [API and Data Contracts](./api-and-data-contracts.md) — endpoints, schemas, state machine, database constraints, errors, prompt/context contract, and configuration.
- [Operations, Testing, and Rollout](./operations-testing-rollout.md) — privacy, safety, telemetry, SLOs, cost controls, test matrix, launch gates, and rollback.
- [Implementation Plan](./implementation-plan.md) — ordered, checkbox-based work breakdown with proposed files and acceptance criteria.

## Acceptance Summary

The first slice is complete only when all of the following are true:

- An authenticated, enabled user can send a text message and receive one persisted assistant response.
- The same `client_message_id` never creates a duplicate user or assistant message.
- A user cannot access or clear another user's conversation, even by guessing identifiers.
- Two concurrent sends on the same thread cannot produce crossed or duplicated replies.
- AI work occurs outside open database transactions.
- Provider failure leaves a recoverable failed assistant placeholder rather than a permanently busy thread.
- History survives process restart and is cursor-paginated.
- Clearing the thread and deleting the account remove all chat rows through explicit/cascade deletion.
- No raw chat text, prompt, profile payload, email, Firebase claim, or provider response is emitted to logs or telemetry.
- New application/domain code introduces no additional import-linter exemptions.
- Critical orchestration, ownership, idempotency, concurrency, and failure paths have full test coverage.

## Proposed Product Defaults

These values are intentionally configurable and should be confirmed before implementation:

| Setting | Proposed beta default |
|---|---:|
| Input length | 4,000 Unicode characters |
| Latest history returned | 50 messages |
| History context sent to model | 20 messages and 24,000 characters, whichever is reached first |
| Output limit | 800 model tokens |
| Provider timeout | 25 seconds |
| Burst limit | 10 sends per minute per authenticated user |
| Concurrent turns | 1 per thread |
| Automatic retention | No scheduled purge in one-user beta; 180-day policy required before broad release |

## Review Decisions Required

Before implementation begins, product/engineering should explicitly approve:

1. Whether the first assistant may use today's aggregate calories/macros, or should launch as history-only chat.
2. The exact health and emergency disclaimer copy for all seven supported languages.
3. Retention duration and whether users need data export in addition to clear/delete.
4. Daily message quota before expanding beyond the one-user allowlist.
5. Whether limited Markdown is supported by the mobile client or responses must be plain text.

No runtime source, migration, route, or dependency change is included in this documentation branch.