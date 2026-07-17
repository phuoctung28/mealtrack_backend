# Single-Thread Chatbot Contracts

**Status:** Proposed

The original combined contract has been split to follow the repository's documentation size guideline:

- [Public API Contract](./api-contracts.md) — routes, request/response schemas, ownership, idempotency, and errors.
- [Persistence Contract](./persistence-contracts.md) — tables, constraints, state transitions, concurrency, pagination, and deletion.
- [AI and Context Contracts](./ai-and-context-contracts.md) — completion port, provider routing, MealTrack snapshot, prompt, output, and configuration.

These three files together are the normative contract for the first single-thread chatbot slice.