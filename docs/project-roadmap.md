# MealTrack Backend - Project Roadmap

**Version:** 0.4.9
**Last Updated:** January 19, 2026
**Status:** Production-ready. 417 source files, ~37K LOC across 4 layers. 681+ tests, 70%+ coverage.
**Architecture**: 4-Layer Clean Architecture + CQRS + Event-Driven with PyMediator singleton registry.

---

## Completed Phases

### January 2026: Documentation Refresh v0.4.8
- [x] Scout-based codebase analysis (4 comprehensive reports: API, App, Domain, Infra layers).
- [x] Updated all documentation with verified statistics (417 files, ~37K LOC).
- [x] Accurate metrics: 29 commands, 23 queries, 10+ events, 40+ handlers, 50+ domain services.
- [x] Added WebSocket chat details (ConnectionManager, 3 application services).
- [x] Documented EventBus singleton registry pattern.
- [x] Updated layer statistics (74/136/130/77 files, ~8K/6K/14K/9K LOC).

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

## Current Priorities (Q1 2026)
1. **Performance**: Optimize suggestion generation (target <10s from ~45s).
2. **Monitoring**: Implement observability (request tracing, performance metrics, error tracking).
3. **Rate Limiting**: Add rate limits to AI-heavy endpoints (meal analysis, suggestions).
4. **Security**: Restrict CORS in production, implement request body logging with PII redaction.

---

## Future Roadmap

### Q2 2026
- [ ] Apple HealthKit & Google Fit sync.
- [ ] Receipt scanning and parsing.
- [ ] Personalized variety optimization algorithms.

### Q3 2026
- [ ] Social sharing & community meal libraries.
- [ ] Voice-based meal logging.
- [ ] Multi-region deployment.

---

## Technical Debt & Maintenance
- [ ] Fix CORS wide open (allow_origins=["*"]) - security risk in production.
- [ ] Enable `daily_meals_router` (currently commented out in main.py).
- [ ] Apply `require_premium` dependency to premium-only features.
- [ ] Refactor hardcoded values (MAX_FILE_SIZE, SLOW_REQUEST_THRESHOLD) to config.
- [ ] Implement API versioning strategy beyond v1.
- [ ] Add monitoring for Gemini API quota and Cloudinary storage limits.
- [ ] Review dev meal seeding to prevent DB clutter in long-running environments.
- [ ] Consider using DI for CloudinaryImageStore instead of direct instantiation in routes.
