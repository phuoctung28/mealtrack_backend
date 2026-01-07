# MealTrack Backend - Project Roadmap

**Version:** 0.4.5
**Last Updated:** January 7, 2026
**Status:** Phase 05 Pinecone Inference Migration Complete. Phase 06 Session-Based Meal Suggestions Active.

---

## Completed Phases

### Phase 06: Session-Based Meal Suggestions (Jan 2026)
- [x] SuggestionOrchestrationService with 4h TTL (Redis).
- [x] Portion multipliers (1-4x) and rejection feedback.
- [x] Generation fallback mechanism.
- [x] 681+ tests passing.

### Phase 05: Pinecone Inference Migration (Jan 2026)
- [x] Recreated indexes with 1024-dim vectors (`llama-text-embed-v2`).
- [x] Migrated to serverless Pinecone Inference API.
- [x] Updated unit/integration tests with 1024-dim mocks.

### Phase 03/04: Refactoring & Cleanup (Dec 2025 - Jan 2026)
- [x] 72% LOC reduction in core domain services.
- [x] Unified Fitness Goal enums (3 canonical values).
- [x] Cleaned up legacy backward compatibility aliases.

### MVP Milestones (2025)
- [x] Gemini 2.5 Flash Vision integration.
- [x] GPT-4 Chat & Planning.
- [x] Firebase Auth & FCM.
- [x] SQLAlchemy 2.0 Async + Alembic (12 migrations).

---

## Current Priorities (Q1 2026)
1. **Performance**: Optimize suggestion generation time from ~45s to <10s.
2. **Infrastructure**: Refactor documentation into modular structures (In Progress).
3. **Analytics**: Implement user engagement and nutritional progress tracking.

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
- [ ] Refactor `PromptGenerationService` (currently >5000 tokens).
- [ ] Enhance WebSocket test coverage for edge cases.
- [ ] Implement request/response logging middleware.
