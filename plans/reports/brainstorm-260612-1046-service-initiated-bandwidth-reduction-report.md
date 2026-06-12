# Service-Initiated Bandwidth Reduction — Design Report
**Date:** 2026-06-12 | **Branch:** feature/NM-affiliate-outbox-pattern

---

## Problem Statement

Render metrics show high "Service-Initiated" (server-outbound) network usage. Root cause: the server acts as a relay for full-size phone images (~5MB) before forwarding them to Cloudinary. This single step accounts for ~96% of service-initiated bandwidth.

---

## Investigation Findings

### Active outbound calls per meal scan
| Step | Outbound | % of total |
|------|----------|------------|
| `cloudinary.uploader.upload()` — original image | ~5MB | 96% |
| Gemini vision — compressed image as base64 | ~200KB | 4% |
| `cloudinary.api.resource()` — URL lookup (fallback only) | ~1KB | <1% |

### Dead code found (no production effect)
- `meal_analysis_event_handler.py` + `load_async`: `MealImageUploadedEvent` is never published → Cloudinary re-download path is dead
- `CloudflareImageGenerator`, `PollinationsImageGenerator`, `ImagenImageGenerator`, `UnsplashImageAdapter`: class definitions, never imported in handlers
- `analyze_by_url_with_strategy`: exists but broken (passes URL text bytes as fake image data to Gemini)

### Key file locations
- `src/infra/adapters/cloudinary_image_store.py` — `save_async` → `save` → `cloudinary.uploader.upload()`
- `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:128` — calls `save_async` with raw `command.file_contents`
- `src/infra/adapters/vision_ai_service.py:27` — `_compress_image()`: caps to 768px/200KB, already applied before Gemini
- `src/infra/services/ai/providers/gemini_provider.py:139` — always converts image bytes to `data:` URI

---

## Chosen Solution: Two-Phase Bandwidth Reduction

### Phase 1 — Server-side compression before Cloudinary upload
**Ships without mobile changes.**

Apply `_compress_image()` (or a shared compression utility) before `save_async`. The same bytes can be reused for Gemini — one compression pass serves both.

```
Before: 5MB raw → Cloudinary (5MB); 5MB raw → _compress_image → 200KB → Gemini
After:  5MB raw → _compress_image → ~400KB → Cloudinary; same 400KB → Gemini
```

Trade-off: Cloudinary stores compressed images (~768px). Acceptable for a meal tracker — thumbnails are 100–300px, detail views are ≤600px.

**Expected reduction:** ~5.2MB → ~400KB per scan (92% reduction).

### Phase 2 — Presigned direct upload (requires mobile release)
Server generates a signed Cloudinary upload token. Client uploads image directly to Cloudinary. Server receives only the resulting URL and handles analysis.

**New endpoint:** `GET /api/v1/meals/upload-token`  
Returns:
```json
{
  "image_id": "<uuid>",
  "cloud_name": "...",
  "api_key": "...",
  "timestamp": 1718179200,
  "signature": "<hmac-sha1>",
  "folder": "mealtrack",
  "public_id": "mealtrack/<uuid>"
}
```

**Updated scan endpoint:** `POST /api/v1/meals/scan` accepts `image_url` instead of file bytes.

**Analysis path after presigned upload:**
- Safe path: server downloads compressed image from Cloudinary URL → sends to Gemini (200KB)
- Optimal path: server passes URL to Gemini directly (test first — Gemini Flash supports `Part.from_uri()` for public HTTPS URLs natively; LangChain behavior needs verification)

**Expected reduction Phase 2:** ~400KB → ~200KB/scan (safe path), or ~1KB (URL Gemini path).

---

## Implementation Plan

### Phase 1 tasks
1. Extract compression into `src/infra/utils/image_compression.py` — shared utility, no coupling to VisionAIService
2. Apply compression in `_handle_parallel_upload` before `save_async`
3. Remove redundant compression call in vision service (DRY — now same bytes from handler)
4. Unit tests: verify compressed size ≤ 200KB, dimensions ≤ 768px

### Phase 2 tasks
1. `CloudinaryImageStore.generate_upload_signature(image_id)` method
2. New route: `GET /api/v1/meals/upload-token` (auth required)
3. `POST /api/v1/meals/scan` accepts `image_url: str` (no file), validates Cloudinary domain
4. Refactor `analyze_by_url_with_strategy` to correctly pass URL to Gemini
5. Test Gemini URL support (`Part.from_uri()` with Cloudinary CDN URL)
6. If URL-based works: update Gemini provider to detect URL vs bytes input
7. Dead code removal: event handler, broken URL analysis, unused image generators

### Phase 2 security constraints
- Signature scoped: `folder=mealtrack`, specific `public_id`, expires in 60s
- Accept-only-from-Cloudinary validation on `image_url` field (domain allowlist)
- Server controls `image_id` generation — client cannot choose arbitrary public_id

---

## Risks

| Risk | Mitigation |
|------|-----------|
| 768px images look bad on high-DPI displays | Test on real device before shipping; can increase to 1200px if needed |
| Gemini URL-based vision not working via LangChain | Safe fallback (download → bytes) already defined; test before committing |
| Client upload to Cloudinary fails silently | Server must validate that `image_url` resolves before kicking off analysis |
| URL expiry during upload (60s) | Generate token with generous TTL (300s) since upload time varies |

---

## Success Metrics
- Render "Service-Initiated" daily bandwidth: ≥90% reduction after Phase 1
- Per-scan server outbound: ≤400KB after Phase 1, ≤200KB after Phase 2
- No regression in meal analysis accuracy or latency (±500ms acceptable)
