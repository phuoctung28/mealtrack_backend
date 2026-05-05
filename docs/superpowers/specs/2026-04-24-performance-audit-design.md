# Backend Performance & Cleanup Audit

**Date:** 2026-04-24  
**Status:** Design doc only  
**Scope:** MealTrack Backend (FastAPI) + Mobile API Contract (Flutter)

---

## Executive Summary

This audit examines the MealTrack backend for performance bottlenecks, unused endpoints, and load capacity concerns. The mobile app (nutree_ai) was also analyzed to identify API contract gaps.

### Key Findings

| Category | Finding | Impact |
|----------|---------|--------|
| **Performance** | Meal suggestion pipeline takes 6-15s | User experience |
| **Performance** | External API cascade (T2→T3) adds 2-5s on cache miss | Latency |
| **Dead Code** | 5 unused backend endpoints | Maintenance burden |
| **API Gap** | 5 mobile referral endpoints have no backend | 404 errors |
| **Load Capacity** | DB pool: 20+10 overflow, Redis: single instance | Scaling ceiling |

### Recent Performance Work (Already Completed)

- Redis cache for nutrition data with T2/T3 timeouts
- Batch ANN query for vector cache (single round-trip)
- Parallelized image fetch for cache misses in `/discover`
- Recipe timeout tightened to 20s
- Accept partial results (min 1 instead of 2)

### Recommended Priority

1. Remove dead endpoints (low effort, reduces maintenance)
2. Document referral API gap (enables mobile fix)
3. Performance optimizations (prioritized by impact/effort)

---

## 1. Performance Bottlenecks

### 1.1 Meal Suggestion Pipeline (6-15s total)

**Current Flow:**
```
/v1/meal-suggestions/generate or /discover
    │
    ├─ Phase 1: Generate Names (1-2s)
    │   └─ Single Gemini call, 20s timeout
    │
    ├─ Phase 2: Generate Recipes (6-8s)
    │   ├─ Parallel recipe generation (4 tasks)
    │   ├─ Early-stop after 3 successes
    │   └─ Nutrition lookup per ingredient (T1→T2→T3)
    │
    └─ Phase 3: Translation (2-3s, non-English only)
        └─ DeepL batch translation
```

**Bottleneck:** Phase 2 nutrition lookup cascade — each ingredient may hit T2 (FatSecret, 2s) or T3 (AI, 3s) if not in Redis/DB.

**Optimization Opportunities:**

| Optimization | Effort | Impact | Notes |
|--------------|--------|--------|-------|
| Pre-warm Redis cache for common ingredients | Low | Medium | ~500 common foods cover 80% of recipes |
| Batch T2 lookups instead of per-ingredient | Medium | High | FatSecret supports batch queries |
| Reduce T3 timeout from 3s to 2s | Low | Low | Accept more zero-cal fallbacks |

### 1.2 Image Fetching in `/discover` Endpoint

**Current Flow:**
```
6 meals generated
    │
    ├─ Batch vector cache lookup (optimized ✓)
    │
    ├─ Cache hits: instant
    │
    └─ Cache misses: parallel fetch (3s timeout each)
        └─ Unsplash/Pexels API calls
```

**Bottleneck:** Cache misses trigger external API calls. Already parallelized, but first-time meals still wait.

**Optimization Opportunities:**

| Optimization | Effort | Impact | Notes |
|--------------|--------|--------|-------|
| Background job to pre-fetch trending meal images | Medium | Medium | Reduces cold-start latency |
| Return placeholder immediately, update async | Medium | High | Better perceived performance |
| Increase cache TTL (currently 24h) | Low | Low | Trade freshness for speed |

### 1.3 Nutrition Lookup Three-Tier Cascade

**Current Tiers:**
```
Redis Cache (24h TTL)
    ↓ miss
T1: food_reference table (exact match)
    ↓ miss  
T2: FatSecret API (2s timeout)
    ↓ miss/timeout
T3: AI estimate (3s timeout)
```

**Bottleneck:** T2 and T3 add significant latency on cache miss. T3 is a last resort that logs warnings.

**Optimization Opportunities:**

| Optimization | Effort | Impact | Notes |
|--------------|--------|--------|-------|
| Bulk seed food_reference with USDA data | Medium | High | Reduces T2/T3 hits |
| Cache T2 results to food_reference | Done | - | Already implemented |
| Parallel T2 lookups for all missing ingredients | Low | Medium | Currently sequential |

### 1.4 External API Timeout Summary

| Service | Current Timeout | Typical Latency | Risk |
|---------|----------------|-----------------|------|
| Gemini (recipe gen) | 20s | 2-8s | High variance |
| FatSecret | 30s (client), 2s (lookup) | 0.5-2s | Rate limits |
| DeepL | implicit | 1-3s | Per-text billing |
| Unsplash/Pexels | 5s | 0.5-2s | Rate limits |
| RevenueCat | 10s | 0.2-1s | Subscription checks |

---

## 2. Endpoint Cleanup

### 2.1 Unused Backend Endpoints (Remove)

| Endpoint | File | Reason |
|----------|------|--------|
| `POST /v1/daily-meals/suggestions` | `daily_meals.py:30` | Router commented out in `main.py` |
| `POST /v1/daily-meals/suggestions/{meal_type}` | `daily_meals.py:84` | Not called by mobile |
| `GET /v1/daily-meals/profile/{id}/summary` | `daily_meals.py:138` | Not called by mobile |
| `GET /v1/daily-meals/health` | `daily_meals.py:162` | Not called by mobile |
| `GET /v1/meal-suggestions/image` | `meal_suggestions.py:389` | Not called by mobile |

**Files to Delete:**
- `src/api/routes/v1/daily_meals.py` (175 lines)

**Cleanup Checklist:**
- [ ] Remove `daily_meals.py` route file
- [ ] Remove `GET /image` endpoint from `meal_suggestions.py`
- [ ] Remove commented import from `main.py`
- [ ] Check for orphaned schemas in `src/api/schemas/`
- [ ] Check for orphaned mappers in `src/api/mappers/`
- [ ] Check for orphaned commands/queries in `src/app/`

### 2.2 Mobile-Backend API Gap (Referral Endpoints)

**Mobile Defines (in `api_service.dart`):**
```dart
POST /v1/referrals/validate   → ValidateCodeResponse
POST /v1/referrals/apply      → void
GET  /v1/referrals/my-code    → MyCodeResponse
GET  /v1/referrals/stats      → ReferralStats
POST /v1/referrals/payout     → void
```

**Backend Status:** No routes, no handlers, no models exist.

**Current Behavior:** Mobile calls return 404 Not Found.

**Recommendation:** 
- Document this gap for future implementation
- Mobile should guard these calls with feature flag until backend is ready
- When implementing: create `src/api/routes/v1/referrals.py`

### 2.3 Admin-Only Endpoints (Keep)

These endpoints exist but aren't called by mobile — they're for admin/internal use:

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/feature-flags/` | List all flags |
| `POST /v1/feature-flags/` | Create flag |
| `PUT /v1/feature-flags/{name}` | Update flag |
| `GET /v1/cache/metrics` | Cache stats |
| All `/health/*` endpoints | Infrastructure monitoring |

---

## 3. Load Capacity Assessment

### 3.1 Database Connection Pooling

**Current Configuration** (`src/infra/database/config.py`):
```python
pool_size = 20
max_overflow = 10
pool_timeout = 30s
connect_timeout = 10s
```

**Capacity:** 30 concurrent DB connections max

| Metric | Status | Concern |
|--------|--------|---------|
| Pool size (20) | Adequate | Sufficient for moderate traffic |
| Overflow (10) | Adequate | Handles burst traffic |
| Pool timeout (30s) | High | May cause slow failures under load |

**Recommendations:**

| Optimization | Effort | Impact |
|--------------|--------|--------|
| Add PgBouncer for connection pooling | Medium | High for scale |
| Configure read replica for queries | High | High for read-heavy load |
| Reduce pool_timeout to 10s (fail fast) | Low | Better error handling |

### 3.2 Redis Cache Utilization

**Current Setup:**
```python
socket_timeout = 5.0s
socket_connect_timeout = 5.0s
# Single Redis instance (no cluster)
```

**Cache Keys in Use:**

| Pattern | Purpose | TTL |
|---------|---------|-----|
| `nutrition:{name}` | Per-100g macros | 24h |
| `session:*` | Suggestion sessions | 4h |
| `subscriptions:*` | RevenueCat cache | varies |

| Metric | Status | Concern |
|--------|--------|---------|
| Single instance | Risk | Single point of failure |
| No cluster mode | Limitation | Memory ceiling |
| Graceful degradation | Good | App continues if Redis down |

**Recommendations:**

| Optimization | Effort | Impact |
|--------------|--------|--------|
| Redis Sentinel for HA | Medium | Eliminates SPOF |
| Monitor cache hit rates via Sentry | Low | Visibility |
| Add cache warming on deploy | Low | Reduces cold-start |

### 3.3 External API Rate Limits

| Service | Rate Limit | Current Usage | Risk |
|---------|-----------|---------------|------|
| Gemini | 60 RPM (free tier) | ~2-4 calls/suggestion | High at scale |
| FatSecret | 5000/day | Per ingredient miss | Medium |
| Unsplash | 50/hour (demo) | Per image miss | High |
| Pexels | 200/hour | Fallback for Unsplash | Medium |
| DeepL | 500k chars/month (free) | Per translation | Medium |

**Recommendations:**

| Optimization | Effort | Impact |
|--------------|--------|--------|
| Upgrade Gemini to paid tier | Cost | Removes RPM limit |
| Implement request queue with rate limiting | Medium | Prevents 429 errors |
| Cache more aggressively (longer TTLs) | Low | Reduces API calls |
| Pre-generate popular meal suggestions | Medium | Reduces real-time API calls |

### 3.4 Horizontal Scaling Readiness

| Component | Stateless? | Scale-Ready? | Notes |
|-----------|-----------|--------------|-------|
| FastAPI app | Yes | Yes | Can run multiple instances |
| PostgreSQL | N/A | Partial | Need read replicas |
| Redis | N/A | No | Single instance |
| Event Bus (PyMediator) | Yes | Yes | Singleton per instance OK |
| Background jobs | No | No | No distributed task queue |

**Missing for Horizontal Scale:**
- Distributed task queue (Celery/ARQ) for background jobs
- Redis cluster or Sentinel
- Load balancer health checks (exist but basic)

---

## 4. Prioritized Recommendations

### P0: Quick Wins (< 1 day effort)

| # | Recommendation | Impact | Effort |
|---|----------------|--------|--------|
| 1 | Remove `daily_meals.py` | Maintenance | 1 hour |
| 2 | Remove `GET /meal-suggestions/image` | Maintenance | 30 min |
| 3 | Reduce pool_timeout to 10s | Reliability | 15 min |
| 4 | Add cache hit rate logging | Visibility | 2 hours |
| 5 | Document referral API gap | Clarity | 1 hour |

### P1: Medium Impact (1-3 days effort)

| # | Recommendation | Impact | Effort |
|---|----------------|--------|--------|
| 6 | Pre-warm Redis with common ingredients | Latency -20% | 1 day |
| 7 | Parallel T2 lookups | Latency -10% | 1 day |
| 8 | Return placeholder images, fetch async | Perceived perf | 2 days |
| 9 | Implement rate limit queue | Reliability | 2 days |
| 10 | Add Redis Sentinel | Availability | 2 days |

### P2: Architectural Improvements (1+ week effort)

| # | Recommendation | Impact | Effort |
|---|----------------|--------|--------|
| 11 | Pre-generate popular meals | Latency -50% | 1 week |
| 12 | Add distributed task queue | Scale | 1 week |
| 13 | PostgreSQL read replica | Scale | 1 week |
| 14 | Upgrade to Gemini paid tier | Scale | Cost |
| 15 | Implement referral backend | Feature | 1-2 weeks |

### Implementation Sequence

```
Week 1: P0 items (cleanup + visibility)
    └─ Remove dead code, add monitoring

Week 2-3: P1 items (latency + reliability)  
    └─ Cache warming, parallel lookups, rate limiting

Week 4+: P2 items (scale + features)
    └─ Based on traffic growth and priorities
```

---

## 5. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| `/discover` p95 latency | ~8-12s | <6s | Sentry performance |
| `/generate` p95 latency | ~12-15s | <10s | Sentry performance |
| Redis cache hit rate | Unknown | >80% | Add logging (P0 #4) |
| T3 AI fallback rate | Unknown | <5% | Existing WARNING logs |
| 404 errors (referrals) | Present | Zero | Fix mobile or implement backend |

---

## Appendix: Files Referenced

**Backend:**
- `src/api/routes/v1/meal_suggestions.py` — Suggestion endpoints
- `src/api/routes/v1/daily_meals.py` — Unused, to be removed
- `src/domain/services/meal_suggestion/parallel_recipe_generator.py` — Recipe pipeline
- `src/domain/services/meal_suggestion/nutrition_lookup_service.py` — 3-tier lookup
- `src/infra/database/config.py` — DB pool settings
- `src/infra/cache/redis_client.py` — Redis client

**Mobile:**
- `lib/core/network/api_service.dart` — API endpoint definitions
