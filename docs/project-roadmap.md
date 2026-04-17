# MealTrack Backend - Project Roadmap

**Version:** 0.6.1
**Last Updated:** April 17, 2026
**Status:** Production-ready. 430 source files, ~38K LOC across 4 layers (API: 76, App: 140, Domain: 133, Infra: 80). 681+ tests, 70%+ coverage.
**Architecture**: 4-Layer Clean Architecture + CQRS + Event-Driven with PyMediator singleton registry + Sentry monitoring.

---

## Completed Phases

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
- [x] SQLAlchemy 2.0 with request-scoped sessions (20 connections + 10 overflow).
- [x] RevenueCat subscription integration.
- [x] Redis caching with graceful degradation (50 connections, 1h default TTL).
- [x] 11 database tables with Meal aggregate state machine.
- [x] 3 application services (MessageOrchestrationService, AIResponseCoordinator, ChatNotificationService).

---

## Current Priorities (Q2 2026)
1. **Performance**: Optimize suggestion generation (target <10s from ~45s).
2. **Rate Limiting**: Tune rate limits on meal_suggestions endpoints (discover, generate).
3. **Security**: Restrict CORS in production, implement request body logging with PII redaction.
4. **Testing**: Increase coverage for new meal discovery and notification dedup logic.

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
- [ ] Fix CORS wide open (allow_origins=["*"]) - security risk in production
- [ ] Implement API versioning strategy beyond v1
- [ ] Apply `require_premium` dependency to premium-only features
- [ ] Refactor hardcoded values (MAX_FILE_SIZE, SLOW_REQUEST_THRESHOLD) to config

### Medium Priority
- [ ] Enable `daily_meals_router` (currently commented out in main.py) or deprecate
- [ ] Add monitoring for Gemini API quota and Cloudinary storage limits
- [ ] Consider using DI for CloudinaryImageStore instead of direct instantiation in routes
- [ ] Tune rate limiting thresholds for meal_suggestions endpoints based on usage patterns

### Low Priority
- [ ] Review dev meal seeding to prevent DB clutter in long-running environments
- [ ] Document meal discovery image search quality thresholds
