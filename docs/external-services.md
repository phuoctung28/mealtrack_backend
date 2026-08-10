# Backend External Services

**Status:** Evergreen integration policy (fail-fast vs degrade)  
**Config owner:** `src/infra/config/settings.py` and `.env.example`  
**Adapter owner:** `src/infra/adapters/`, `src/infra/services/`, `src/infra/cache/`, `src/infra/monitoring/`  
**Incident response:** `docs/runbooks/provider-outage.md` and sibling runbooks

Do not treat this file as a provider HOW-TO or env inventory. Discover keys from
settings, wiring from adapters, and live health from OpenAPI `/docs`.

---

## Failure policy matrix

| Dependency | Class | On failure |
|------------|-------|------------|
| PostgreSQL | **Required** | Fail fast (typically 503) |
| Firebase Auth | **Required** | Fail fast (401) |
| AI provider stack | **Required for AI routes** | Circuit breaker → next model in chain; exhausted chain raises `AIUnavailableError` |
| Cloudflare Workers AI | **Optional routed provider** | Skip / fall through; disable via env |
| Cloudinary | **Best-effort media** | Degrade (fallback URL construction where coded) |
| RevenueCat | **Billing sync** | Webhook/cache degrade; last-known subscription where available. Premium route gates are not enforced yet |
| Redis optional caches | **Optional** | Bypass cache; continue from source of truth |
| Redis meal-suggestion sessions | **Required transient state** (current design) | Session writes fail when store unavailable |
| DeepL, FatSecret, USDA, OFF, Brave, image stock APIs | **Optional enrichment** | Degrade to local/prior results when safe |
| PostHog | **Optional analytics** | Skip capture |
| Sentry | **Optional observability** | Local logs only; facade no-ops without DSN |
| nutree-affiliate | **Optional partner** | Validate may return inactive; lifecycle events retry via outbox |

**Redis rule:** optional caches are never the source of truth for nutrition,
notification delivery, FCM token ownership, or write-path correctness. Cache
admission policy: `docs/decisions/260608-2223-selective-cache-admission-policy.md`.

**Privacy rule:** never log prompts, food payloads, raw AI output, base64
images, emails, auth tokens, full barcodes, or secrets. Prefer operation name,
internal IDs, status codes, and error class.

---

## Adapter map (WHERE)

| Concern | Owner paths |
|---------|-------------|
| Settings / env | `src/infra/config/settings.py` |
| Firebase Auth + FCM | `src/infra/services/firebase_service.py`, `firebase_auth_service.py`, `src/infra/services/push/` |
| Cloudinary images | `src/infra/adapters/cloudinary_image_store.py` |
| AI routing / circuit breaker | `src/infra/services/ai/` (`ai_model_manager.py`, providers, adapters) |
| Vision analysis | `src/infra/adapters/vision_ai_service.py` |
| OpenAI prompt-cache policy | `src/infra/services/ai/openai_prompt_cache_policy.py` |
| Food providers (USDA, FatSecret, OFF, Brave) | `src/infra/adapters/food_data_service.py`, `fat_secret_service.py`, `open_food_facts_service.py`, `brave_search_nutrition_service.py` |
| Translation | `src/infra/adapters/deepl_translation_adapter.py` |
| Stock / generated images | `pexels_image_adapter.py`, `unsplash_image_adapter.py`, `imagen_image_generator.py`, `pollinations_image_generator.py`, `cloudflare_workers_image_generator.py` |
| RevenueCat | `src/infra/adapters/revenuecat_adapter.py`; webhook entry in `src/api/routes/v1/webhooks.py` with sibling modules `webhook_subscription_lifecycle.py`, `webhook_referral_funnel.py`, `webhook_lookup_parsing.py` |
| Web funnel redemption | `src/infra/services/web_funnel_*` |
| PostHog | `src/infra/adapters/posthog_adapter.py` |
| Resend email | `src/infra/adapters/resend_email_adapter.py` |
| Redis | `src/infra/cache/` |
| Sentry / observability facade | `src/infra/monitoring/`, `src/observability.py` |
| Affiliate outbox client | `src/infra/adapters/affiliate_service_adapter.py`; cron `src/cron/affiliate_outbox.py` |
| DB pool | `src/infra/database/config_async.py`, `connection_policy.py` — see `database-guide.md` |

---

## Non-derivable integration rules

### AI provider routing

- Runtime registry is **OpenAI + optional Cloudflare Workers AI**. Gemini
  packages may remain in dependencies but are not registered as a runtime
  provider unless code changes that fact.
- `AIModelManager` owns per-purpose fallback chains and the circuit breaker
  (failures open the breaker; recovery is coded in the manager).
- Text and vision Cloudflare paths are independent (LangChain text vs REST
  vision). Vision model IDs and purpose lists are settings-owned — read
  `CLOUDFLARE_WORKERS_AI_*` from settings, not this doc.
- Optional graph workflow (`AI_MEAL_ANALYZE_GRAPH_ENABLED`) must not change
  provider order or READY meal API contracts.
- Optional FatSecret meal validation is never required for a valid scan.
- Prompt cache (OpenAI Responses via LangChain) is best-effort; keys hash
  system prompt only — never raw user text/images. Monitor facade metrics before
  claiming savings.
- Never log `[AI-*]` payloads beyond provider, model alias, purpose, status,
  error class.

### Barcode cascade reliability

Order and verification rules (handlers/adapters own exact implementation):

1. Local `food_reference` / cache with GTIN aliases  
2. FatSecret exact barcode  
3. OpenFoodFacts exact barcode  
4. USDA FDC branded exact `gtinUpc` (when key present)  
5. Brave + AI as estimate hints only  
6. AI estimate last  

Invalid GTIN → 400 before external calls. Exact provider hits may be cached as
verified data. Brave-only / name-only / AI estimates return `is_estimate=true`
and must not enter the global catalog. Logs must not include full raw barcodes.

### Redis cache posture

| Data | Policy |
|------|--------|
| Food search/details, nutrition lookup, AI cost caches | Optional cache-aside; miss/error → source of truth |
| Auth UID mapping | Process-local TTL, not Redis |
| Notification rows / FCM ownership | Database only — do not cache as source of truth |
| Meal suggestion sessions | Required Redis-backed transient state today |

Default: do not cache. Admission checklist lives in the selective-cache decision
above. `FAIL_ON_CACHE_ERROR=false` is the expected production posture for
optional caches.

### RevenueCat and web redemption

- Webhooks update local `subscriptions`; signature verification is constant-time.
- Web checkout handoff is `/v1/web-funnel/*` (hash-only redemption link, Firebase
  passwordless, preflight/finalize). Contracts: `api-endpoints.md`.
- Billing ownership is RevenueCat Web; legacy direct Paddle fulfillment is gone.
- Premium feature gates are planned, not enforced on routes.

### Sentry ownership

- Runtime code uses the `src.observability` facade only. Direct `sentry_sdk`
  imports belong in `src/infra/monitoring/sentry.py`.
- One root-cause ERROR per unexpected request failure (API exception handlers).
  Do not log-and-rethrow (duplicate Sentry issues). Background/cron boundaries
  own their own capture when they swallow exceptions.
- Expected 4xx domain failures are silent at ERROR level.
- Severity contract: INFO = normal; WARNING = degrade/retry/slow; ERROR =
  user-impacting; CRITICAL = service unusable. Same privacy allowlist as above.
- Use Sentry metrics for operational AI failure alerts; use PostHog for product
  / LLM product traces — not P1 outage paging.

### nutree-affiliate boundary

MealTrack and nutree-affiliate are **separate services and databases**. Never
join or write affiliate tables from MealTrack.

- Sync path: HMAC-signed HTTP via `affiliate_service_adapter` +
  `affiliate_event_outbox` + cron dispatcher.
- Identity: `mealtrack_user_id` here; `affiliate_id` only in affiliate service.
- Architecture ownership table: `system-architecture.md` → Affiliate System
  Boundary.
- Signing contract and outbox retry live in the adapter, model, and
  `tests/unit/infra/adapters/test_affiliate_service_adapter_signing.py`.

### Health surfaces

Discover paths in OpenAPI. Typical ops probes: `/health`, `/v1/health/db-pool`,
`/v1/health/db-connections`, `/v1/health/notifications`.

---

## Related

- Architecture: `system-architecture.md`
- Database: `database-guide.md`
- HTTP conventions: `api-endpoints.md`
- Provider outage: `runbooks/provider-outage.md`
