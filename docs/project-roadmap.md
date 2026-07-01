# MealTrack Backend - Project Roadmap

**Version:** 0.6.6
**Last Updated:** June 27, 2026
**Status:** Production-ready. 627 source files in `src/`, 53,972 LOC in `src/`, 306 Python test files, and 1,600+ collected tests. Default `pytest` is unit-biased because integration tests are ignored by config.
**Architecture**: 4-Layer Clean Architecture + CQRS + Event-Driven with PyMediator singleton registry + Sentry monitoring.

---

## Completed Phases

### June 2026: Python 3.13 and Dependency Standardization
- [x] Upgraded runtime, Docker, CI, and documented backend baseline to Python 3.13.
- [x] Upgraded FastAPI and core production libraries to current Python 3.13-compatible releases.
- [x] Pinned direct production and test dependencies for reproducible local, CI, and Docker installs.
- [x] Removed unused `fatsecret` package dependency; runtime FatSecret integration uses the in-repo HTTP adapter.
- [x] Upgraded pytest tooling to 9.x to clear the test dependency audit finding.
- [x] Verified `requirements.txt` and `requirements-test.txt` with `pip-audit`; ML-only resolver dependencies are no longer shipped.

### June 2026: Journey Progress Card
- [x] Added canonical `GET /v1/progress/journey` for the dashboard progress card.
- [x] Strict active-period filtering keeps only `period_start <= action_time < period_end`; existing users without `goal_started_at` fall back to the stable 2026-06-21 feature start in their local timezone.
- [x] Onboarding and target-weight updates now set the journey baseline fields that anchor the active period.
- [x] Existing-user migration can now seed journey progress from pre-release action logs with a bounded `journey_progress_seed_percent`, while post-release actions continue filling the remaining progress.

### June 2026: Provider and Contract Refresh
- [x] OpenAI is the default AI provider for text and vision; configured Cloudflare Workers AI can prepend text-purpose chains and append vision fallbacks.
- [x] OpenAI model ownership is explicit in `src/infra/services/ai/ai_model_manager.py` with `gpt-5.4-mini-2026-03-17` as the base default.
- [x] Upload-token smoke coverage is part of the current API verification set.
- [x] `pydantic-settings` and the CI/test default flow were updated to Python 3.13.2, FastAPI 0.136.3, and unit-biased pytest defaults.

### June 2026: Single-Owner Logger System
- [x] Established log-or-raise rule: one root-cause `ERROR` per unexpected request failure; expected 4xx exceptions produce zero ERROR logs.
- [x] `src/api/exception_handlers.py` — new central exception boundary with `register_exception_handlers(app)`; owns single ERROR for unexpected exceptions.
- [x] `RequestLoggerMiddleware` — 5xx response lines downgraded from ERROR to WARNING (outcome indicator only).
- [x] `handle_exception()` in `src/api/exceptions.py` — pure conversion helper, no ERROR log before re-raise.
- [x] All command/query handlers — removed `logger.error` before re-raise patterns.
- [x] `src/infra/services/ai/ai_model_manager.py` — emits `log_event("warning", "ai.provider.failure")` before raising `AIUnavailableError`.
- [x] Cron entrypoints — emit `log_event("info", "cron.phase.completed")` per phase; `capture_exception` + `flush_observability` on failure.
- [x] `src/infra/services/affiliate_outbox_dispatch_service.py` — emits `increment_metric("affiliate.outbox.failure")` for permanent failures.
- [x] Architecture guardrails: `tests/unit/architecture/test_logging_ownership_guardrails.py` and `tests/unit/api/test_single_owner_exception_logging.py`.

### June 2026: Observability Connector
- [x] Added provider-neutral observability facade with no-op fallback and Sentry connector.
- [x] Isolated all direct `sentry_sdk` usage to `src/infra/monitoring/sentry.py`.
- [x] Migrated API startup, request context, cron flush/capture, and affiliate outbox permanent failure alerts through the facade.
- [x] Enabled configurable Sentry Logs, operational metrics, and explicit profile session settings through the connector.
- [x] Added safe scalar attribute filtering for logs and metrics.
- [x] Documented Sentry event contract, safe context allowlist, and alert/dashboard setup guidance.
- [x] Normalized production log severity semantics and removed raw AI response,
      image URL, email, and webhook provider identifiers from representative
      application logs.

### June 2026: Vision Parser Resilience
- [x] Food-label custom nutrition now preserves fiber and sugar through manual meal creation, meal edit requests, response mapping, and serving-size recalculation, with gram-based per-100g validation extended to the new fields. Completed 2026-06-28.
- [x] Canonical AI nutrition contracts now reject impossible over-limit food quantities before domain hydration, invalid AI items now fail instead of being silently repaired, and structured meal image/text output retries exactly once before raising controlled `AIOutputValidationError`.
- [x] Meal image analysis now carries an explicit `is_food` guard through provider schema validation, adapter mapping, parsers, command handlers, and API error mapping so explicit non-food images reject before nutrition parsing without changing successful meal response shape.
- [x] LLM nutrition output contracts: Structured Pydantic contracts for all AI meal-analysis flows; bounded validation retry; parser becomes deterministic mapping; `quantity=150000` and similar impossible AI outputs are rejected before persistence. Background event handler sanitizes `AIOutputValidationError` into a user-friendly failure message. `PromptEvalLoop` tracks schema `validation_success_rate` as a separate observable metric alongside `parse_success_rate`.
- [x] Meal image scans now treat caloric beverages as normal scanned meals; hydration logging remains explicit through `/v1/hydration/*`, with legacy `scan_beverage` hydration rows supported only for historical compatibility.

### June 2026: Normalized Database Foundation
- [x] Added normalized profile preferences, hydration entries, saved suggestion items/steps, meal instruction steps, food serving sizes, and food nutrient tables.
- [x] Added typed payout workflow fields while retaining raw payout details pending a later security/contract pass.
- [x] Documented notification context as render snapshot only; recipient truth remains in `user_fcm_tokens`.
- [x] Production migration runner is Alembic-only and no longer creates/stamps schema from `Base.metadata`.
- [x] Local Postgres upgrade verified to Alembic head `20260609000006`.

### June 2026: Neon Direct Pool + Async Library Alignment
- [x] Explicit DB connection mode resolver: `direct_pool` uses a dedicated async queue pool against the direct Neon URL; `neon_pooler` uses `NullPool` with PgBouncer-safe asyncpg settings.
- [x] `APP_DATABASE_URL` is the app runtime URL; `DATABASE_URL_DIRECT` is migration/admin only — no silent priority drift.
- [x] `FoodDataService` converted from `requests` to `httpx.AsyncClient`.
- [x] Cloudinary blocking SDK calls wrapped with `asyncio.to_thread` off-loop boundary.
- [x] Static guard blocks uncontained `requests` imports under `src/infra/adapters`.
- [x] Health endpoint (`/v1/health/db-pool`) reports connection mode, pool type, and capacity.
- [x] `.env.example`, `docs/database-guide.md`, and `docs/external-services.md` updated to match runtime contract.
- [x] Completed 2026-06-10.

### June 2026: Async Repository Consolidation
- [x] Runtime database access consolidated to async SQLAlchemy: FastAPI dependencies, cron jobs, handlers, repositories, and UoW use `AsyncSession`.
- [x] Deleted the sync unit-of-work runtime, sync database config, and legacy sync repositories after replacing remaining test consumers with explicit test-only facades.
- [x] Architecture guard now expects zero sync DB runtime imports in `src` and no broad sync repository transition allowlist.
- [x] Default validation: `pytest -q` passes (`1499 passed, 3 skipped`).

### June 2026: Weekly Budget Resilience
- [x] Weekly budget meal loading now quarantines malformed legacy `READY` rows without nutrition before domain hydration.

### June 2026: iOS Notification Payload Hardening
- [x] Removed obsolete direct notification service wiring and direct meal/summary helper sends.
- [x] Removed background push scheduler lifecycle, scheduler leader lock, stale test notification route, and misleading legacy push/email service names; cron entrypoints now own notification/email work.
- [x] `FirebaseService` rejects blank display text before sending APNs payloads and mobile `data` fields.
- [x] iOS/APNs payload tests cover non-empty alert title/body for valid sends and fail-closed behavior for blank-input sends.

### May 2026 (late): Notification Overhaul, RevenueCat Webhook Expansion, Meal-Suggestion Parallel Generator
- [x] Platform-specific FCM payload builders: `android_payload_builder.py` (high-priority, channel IDs), `apns_payload_builder.py` (APNs Time Sensitive, `interruption-level` in payload body)
- [x] Trial-expiry push notifications at T-2d and T-1d via `CronTrialPushService`
- [x] Timezone-change notification reschedule in `UpdateTimezoneCommandHandler` and `RegisterFcmTokenCommandHandler`
- [x] `DailyContextPrecomputeService`: batch pre-computes user calorie context for timezone-local dates
- [x] `src/cron/push.py`: Render cron pipeline for precompute, trial-expiry scheduling, due-row FCM dispatch, and expired-row cleanup
- [x] RevenueCat webhook full lifecycle: INITIAL_PURCHASE, RENEWAL, CANCELLATION, EXPIRATION, BILLING_ISSUE, PRODUCT_CHANGE, REFUND, TRANSFER
- [x] PostHog lifecycle mirroring for subscription events via `PostHogAdapter`
- [x] Referral credit/revoke wired to INITIAL_PURCHASE / REFUND webhooks
- [x] Parallel recipe generator: 3-phase pipeline (name generation → parallel generation → translation)
- [x] `src/cron/email.py`: Render cron pipeline for re-engagement and trial-expiry lifecycle emails

### May 2026 (early): Nutrition Fixes, Referral Improvements, Email Deep Links
- [x] Configurable referral commission rates via `REFERRAL_COMMISSIONS` env var (per-currency JSON)
- [x] Custom unit-to-grams normalization fix in nutrition calculation (`convert_quantity_to_grams`)
- [x] BMR floor raised to 85% of standard daily; cutting deficit reduced 500→300 kcal (clinical floor: 1200F/1500M)
- [x] Email Universal Links: `/.well-known/apple-app-site-association` + `/app-download` redirect
- [x] AsyncUnitOfWork concurrency guard (`asyncio.Lock`); handlers cloned with fresh UoW per dispatch
- [x] Variable-length referral codes: 3–15 characters

### April 2026: Sentry Monitoring, Meal Discovery, Onboarding Redesign
- [x] Sentry SDK integration for error tracking and performance monitoring
- [x] Meal discovery endpoint with image search (Unsplash, Pexels)
- [x] Notification deduplication via notification_sent_log table (migration 047)
- [x] Onboarding redesign fields: challenge_duration, training_types (migration 045)
- [x] Food reference name normalization (migration 046)
- [x] Progress tracking endpoints: streak, daily-breakdown
- [x] Documentation updates: system-architecture, code-standards, project-overview, roadmap

### February 2026: Documentation Refresh v0.5.0
- [x] Updated all documentation with latest scout-verified statistics (430 files, ~38K LOC).
- [x] Accurate metrics: 30 commands, 31 queries, 19 events, 54 handlers, 50+ domain services.
- [x] Fixed metric inconsistencies across all doc files.
- [x] Updated layer statistics (76/140/133/80 files, ~8.6K/6.2K/14.6K/8.9K LOC).
- [x] Added more detail to codebase modules and dependencies.

### January 2026: Documentation Refresh v0.4.8
- [x] Scout-based codebase analysis (4 comprehensive reports: API, App, Domain, Infra layers).
- [x] Updated all documentation with verified statistics (417 files, ~37K LOC).
- [x] Accurate metrics: 29 commands, 23 queries, 10+ events, 40+ handlers, 50+ domain services.
- [x] Added WebSocket chat details (ConnectionManager, 3 application services).
- [x] Documented EventBus singleton registry pattern.

### Phase 06: Session-Based Meal Suggestions (Jan 2026)
- [x] SuggestionOrchestrationService with 4h TTL (Redis).
- [x] Portion multipliers (1-4x) and rejection feedback.
- [x] Generation fallback mechanism.
- [x] 681+ tests passing.

### Phase 02: Language Prompt Integration (Jan 2026)
- [x] Language-aware prompt generation with injected instructions.
- [x] LANGUAGE_NAMES mapping for 7 languages.
- [x] System message customization by language.

### Phase 01: Multilingual Support (Jan 2026)
- [x] 7-language support (en, vi, es, fr, de, ja, zh) with ISO 639-1 codes.
- [x] English fallback for invalid language codes.
- [x] TranslationService for post-generation translation.

### Phase 05: Pinecone Inference Migration (Jan 2026)
- [x] Recreated indexes with 1024-dim vectors (llama-text-embed-v2).
- [x] Migrated to serverless Pinecone Inference API.
- [x] Updated unit/integration tests with 1024-dim mocks.
- [x] Semantic ingredient search with 0.35 similarity threshold.

### Phase 03/04: Refactoring & Cleanup (Dec 2025 - Jan 2026)
- [x] 72% LOC reduction in core domain services.
- [x] Unified Fitness Goal enums (3 canonical values: CUT, BULK, RECOMP).
- [x] Cleaned up legacy backward compatibility aliases.
- [x] Consolidated meal planning services.

### MVP Milestones (2025)
- [x] Gemini 2.5 Flash Vision integration with 6 analysis strategies (Strategy Pattern).
- [x] Multi-model Gemini for rate distribution (4 model types: meal names, recipe primary/secondary, general).
- [x] CQRS architecture with PyMediator event bus (singleton registry pattern).
- [x] Chat with streaming AI responses (WebSocket + REST, MessageOrchestrationService, AIResponseCoordinator).
- [x] Firebase Auth & FCM with platform-specific configs.
- [x] SQLAlchemy 2.0 async runtime with `AsyncUnitOfWork` transaction boundaries.
- [x] RevenueCat subscription integration.
- [x] Selective Redis caching policy documented; optional caches degrade, required state must be modeled separately.
- [x] 11 database tables with Meal aggregate state machine.
- [x] 3 application services (MessageOrchestrationService, AIResponseCoordinator, ChatNotificationService).

---

## Current Priorities (Q2 2026)
1. **Performance**: Optimize suggestion generation (target <10s from ~45s) — in progress.
2. **Security**: Restrict CORS in production (`allow_origins=["*"]` currently wide open), add PII redaction to request logging — open.
3. **Rate Limiting**: Tune rate limits on `meal_suggestions` endpoints (discover, generate) — open.
4. **Testing**: Increase coverage for meal discovery and notification dedup logic — open.
5. **Premium Gating**: Apply `require_premium` dependency to premium-only routes — open.

---

## Future Roadmap

### Q3 2026
- [ ] Apple HealthKit & Google Fit sync.
- [ ] Receipt scanning and parsing.
- [ ] Personalized variety optimization algorithms.
- [ ] Voice-based meal logging.

### Q4 2026+
- [ ] Social sharing & community meal libraries.
- [ ] Multi-region deployment.
- [ ] Advanced analytics dashboard (consumption trends, goal adherence).

---

## Technical Debt & Maintenance

### High Priority
- [ ] Plan contract migration to remove or secure legacy JSON compatibility fields after production observation window.
- [ ] Fix CORS wide open (allow_origins=["*"]) - security risk in production
- [ ] Implement API versioning strategy beyond v1
- [ ] Apply `require_premium` dependency to premium-only features
- [ ] Refactor hardcoded values (MAX_FILE_SIZE, SLOW_REQUEST_THRESHOLD) to config

### Medium Priority
- [ ] Add monitoring for AI provider quota and Cloudinary storage limits
- [ ] Consider using DI for CloudinaryImageStore instead of direct instantiation in routes
- [ ] Tune rate limiting thresholds for meal_suggestions endpoints based on usage patterns

### Low Priority
- [ ] Review dev meal seeding to prevent DB clutter in long-running environments
- [ ] Document meal discovery image search quality thresholds
