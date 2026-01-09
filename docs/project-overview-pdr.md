# MealTrack Backend - Project Overview & Product Development Requirements

**Version:** 0.4.6
**Last Updated:** January 9, 2026
**Status:** Phase 02 Language Prompt Integration Complete. Phase 06 Session-Based Meal Suggestions Active.

---

## Executive Summary

MealTrack Backend is a FastAPI-based service powering intelligent meal tracking and nutritional analysis. It integrates AI vision (Gemini 2.5 Flash) and conversational AI (GPT-4) to provide real-time food recognition and personalized nutrition planning.

---

## 1. Project Vision & Goals

### Vision Statement
Empower users to understand their nutrition through effortless, AI-driven tracking and personalized recommendations.

### Primary Goals
1. **Accuracy**: >90% food recognition accuracy via Gemini Vision.
2. **Efficiency**: Meal logging in < 30 seconds.
3. **Personalization**: Goal-based (CUT, BULK, RECOMP) nutritional targets.
4. **Performance**: API p95 < 500ms.

---

## 2. Core Features

### 1. AI-Powered Meal Analysis
- Detects multiple foods in a single image.
- Estimates portion sizes and macro-nutritional content.
- Returns results in < 3 seconds (READY state machine).

### 2. Session-Based Meal Suggestions (Phase 06)
- Generates 3 personalized suggestions per session.
- Tracks session state in Redis with a 4-hour TTL.
- Supports portion multipliers (1-4x) and rejection feedback.
- **Phase 01 Multilingual**: 7 languages (en, vi, es, fr, de, ja, zh) with fallback to English.
- **Phase 02 Prompt Integration**: Language-aware prompt generation with injected instructions (LANGUAGE_NAMES mapping, helper functions, system message customization).

### 3. Intelligent Meal Planning
- AI-generated 7-day meal plans.
- Respects dietary restrictions (vegan, keto, etc.).
- Ingredient-based planning options.

### 4. Vector Search & Food Discovery (Phase 05)
- Uses Pinecone Inference API with 1024-dimension embeddings.
- Semantic search across proprietary and USDA datasets.

---

## 3. Technical Stack
- **Framework**: FastAPI (Python 3.11+)
- **Database**: MySQL 8.0, Redis 7.0
- **Vector DB**: Pinecone (1024-dim, llama-text-embed-v2)
- **AI Services**: Google Gemini 2.5 Flash, OpenAI GPT-4
- **Storage**: Cloudinary (Images)
- **Auth**: Firebase JWT

---

## 4. Non-Functional Requirements
- **Reliability**: 99.9% uptime.
- **Test Coverage**: >70% overall, 100% critical paths.
- **Maintainability**: Strict 400-line limit per file; 4-Layer Clean Architecture.
- **Security**: AES-256 at rest; TLS in transit; Firebase RBAC.

---

## 5. Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.4.6 | Jan 9, 2026 | Phase 02: Language prompt integration (LANGUAGE_NAMES, language instructions, updated prompts). |
| 0.4.6 | Jan 9, 2026 | Phase 01: Meal suggestions multilingual support (7 languages, ISO 639-1 codes). |
| 0.4.5 | Jan 7, 2026 | Phase 05 Pinecone Migration (1024-dim). Documentation split for modularity. |
| 0.4.4 | Jan 4, 2026 | Phase 03 Cleanup: Unified fitness goal enums to 3 canonical values. |
| 0.4.0 | Jan 3, 2026 | Phase 06: Session-based suggestions with 4h TTL. |
