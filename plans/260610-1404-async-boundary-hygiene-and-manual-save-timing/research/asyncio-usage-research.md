---
type: research
title: "Asyncio usage research"
created: "2026-06-10"
---

# Asyncio Usage Research

## Summary

`asyncio` appears in about 80 active source call sites. Most are acceptable: bounded `wait_for`, vendor-SDK `to_thread`, cron `asyncio.run`, and limited fan-out. Cleanup should target ownership, cancellation, and sync compatibility wrappers.

## Findings

- Event bus publishes domain-event subscribers with untracked `asyncio.create_task`: `src/infra/event_bus/pymediator_event_bus.py:231`.
- Unsplash compliance tracking uses request-local fire-and-forget task: `src/api/routes/v1/meal_suggestions.py:351`.
- Recipe generation early-stop cancels tasks without draining them: `src/domain/services/meal_suggestion/parallel_recipe_generator.py:490`.
- Sync `generate_meal_plan()` wrapper drives an event loop with `run_until_complete`: `src/infra/adapters/meal_generation_service.py:57`, `src/infra/adapters/meal_generation_service.py:84`, `src/infra/adapters/meal_generation_service.py:89`.
- Port docs already warn not to wrap sync meal generation with `asyncio.to_thread`: `src/domain/ports/meal_generation_service_port.py:24`.
- `AsyncUnitOfWork` has an internal per-instance `asyncio.Lock`: `src/infra/database/uow_async.py:85`; useful for protection, but it can hide accidental UoW reuse by serializing instead of failing fast.
- `DailyContextPrecomputeService` stores in-memory locks keyed by date/timezone/user: `src/infra/services/daily_context_precompute_service.py:43`; acceptable short-term, but needs cleanup policy if workers live long.
- Legitimate `to_thread` usage remains for sync vendor SDKs: Cloudinary, DeepL, Resend, Gemini SDK, Firebase auth, and image embedding adapters.

## Recommendation

Add architecture tests for forbidden event-loop driving and unmanaged task creation. Convert fire-and-forget work to a managed background task runner or explicit durable queue semantics. Remove the sync meal generation wrapper if production code no longer needs it.

## Unresolved Questions

None.
