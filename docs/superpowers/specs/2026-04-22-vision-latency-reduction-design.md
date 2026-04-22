# Vision Latency Reduction Design

**Date:** 2026-04-22
**Target:** Consistent 8s or under for `/v1/meals/image/analyze`
**Observed baseline:** 14.67s (variable, dominated by Gemini thinking tokens)

## Problem

The meal image analysis endpoint is slow and inconsistent. A production trace shows:

```
[PHASE-1-START]    vision analysis | attempt=1/2
[PHASE-1-COMPLETE] elapsed=14.67s
[ANALYSIS-COMPLETE] total=14.67s | phase1=14.67s | phase2=0.00s
```

Three root causes in descending impact:

1. **Thinking tokens unconstrained** — `gemini-2.5-flash` runs extended internal reasoning on vision calls. Recipe and barcode paths already set `thinking_budget=0`; the meal scan path does not. This adds 5–15s of variable overhead.
2. **Full-size image sent as base64** — A 725KB JPEG becomes a ~967KB base64 payload. No resize or recompression before encoding. Gemini internally downsamples to ~768px anyway.
3. **No `max_output_tokens` cap** — Unconstrained output allows verbose generation to extend call time unpredictably.

## Approach

Two changes to `src/infra/adapters/vision_ai_service.py`:

### 1. Disable thinking + cap output tokens

On the `get_model()` call used for vision analysis:
- Set `thinking_budget=0` (consistent with recipe/barcode paths)
- Set `max_output_tokens=1024` (vision JSON response is ~300–500 tokens; 1024 gives safe headroom)

Expected impact: drops tail latency from 14.67s to ~4–6s, makes distribution consistent.

### 2. Image compression before base64 encode

Add a private `_compress_image(image_bytes: bytes) -> bytes` method that runs before the base64 encode step:

- Resize to **max 768px** on the longest side using Pillow (already in `requirements.txt`)
- Re-encode as JPEG at **quality 85**
- Skip if the image is already small (under 200KB and longest dimension under 768px)

Expected payload reduction: ~967KB → ~100KB (~10x). Expected additional latency reduction: 1–2s.

**Fallback:** if Pillow raises on a malformed image, log a warning and continue with the original bytes. A slower response is better than a 500.

## Architecture

All changes are confined to `src/infra/adapters/vision_ai_service.py`. No handler, domain, or API layer changes required. Image preprocessing is an infrastructure concern and stays there.

## Data Flow

```
API layer
  → handler
    → vision_ai_service.analyze(image_bytes)
        1. _compress_image(image_bytes)  ← NEW
        2. base64 encode compressed bytes
        3. get_model(thinking_budget=0, max_output_tokens=1024)  ← CHANGED
        4. invoke Gemini with prompt + image payload
        5. return raw vision response
```

## Error Handling

| Failure | Behaviour |
|---|---|
| Pillow raises on corrupt image | Log warning, fall back to original bytes |
| Gemini returns empty response | Existing retry logic handles (max_attempts=2) |
| Gemini times out | Existing retry logic handles |

## Testing

Three unit tests added to the existing vision service test file:

- `test_compress_image_resizes_large_image` — output dimensions ≤ 768px on longest side
- `test_compress_image_skips_small_image` — bytes-in ≈ bytes-out for images already under threshold
- `test_compress_image_fallback_on_corrupt_bytes` — original bytes returned when Pillow raises

Latency improvement is verified in production via the existing `[PHASE-1-COMPLETE] elapsed=Xs` log line.

## Expected Outcome

| Metric | Before | After |
|---|---|---|
| Typical latency | 14.67s | 3–5s |
| Tail latency (p95) | ~15s | ~6s |
| Consistency | High variance | Low variance |
| Analysis quality | Unchanged | Unchanged |
