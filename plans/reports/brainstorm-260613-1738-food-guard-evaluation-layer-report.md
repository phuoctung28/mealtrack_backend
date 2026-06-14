# Food Guard Evaluation Layer — Brainstorm Report

**Date:** 2026-06-13  
**Branch:** delivery  
**Status:** Design agreed, pending plan

---

## Problem Statement

Gemini 2.5 Flash-Lite food scanner (`VisionAIService`) analyzes any image sent to it — including non-food items (laptops, cats, shoes). The current post-analysis check (`has_food`) at lines 165–174 in both command handlers catches this, but **only after the full expensive Gemini call completes**. Goal: reject non-food images earlier and more explicitly.

**Constraints:**
- 0% server CPU overhead (no PIL-for-guard, no CLIP, no PyTorch)
- No new heavy dependencies
- Minimal financial cost

---

## Approaches Evaluated

### 1. Native LLM Guardrails — Single-Stage Augmented ✅ CHOSEN
Add `is_food: bool` to the existing `VISION_ANALYSIS` JSON schema. One Gemini call returns both the food guard result and full nutrition data. Gemini naturally produces minimal output tokens for non-food images (`{"is_food":false,"foods":[],...}`).

**Pros:** Zero extra latency, zero extra API calls, zero new dependencies, cleanest code change (4 files).  
**Cons:** Image input tokens always paid (can't avoid).

### 2. Two-Stage: Tiny Guard Prompt → Full Analysis
Separate Flash-Lite call with minimal "is this food?" prompt before running full nutrition analysis.

**Pros:** Saves input prompt tokens on junk scans.  
**Cons:** Adds ~300–500ms latency to EVERY food scan. Only cost-effective if junk rate >38%. For typical food app usage (<10% junk), **costs 8% more** than single-stage augmented.

### 3. Local Backend CV (CLIP/MobileNet)
**Rejected.** Requires `torch`/`transformers`/`numpy` — violates server CPU + dep constraints.

### 4. Client-Side CoreML
**Rejected.** Platform lock-in (iOS only), bundle size increase, App Store update required for model changes.

### 5. Multimodal Vector Embeddings (`gemini-embedding-2`)
**Rejected.** Requires PIL + numpy for comparison logic on server.

### 6. Cloudinary AI Tagging
**Rejected.** Returns raw object tags, not binary food/not-food. Requires brittle keyword intersection list.

---

## Cost Analysis

Flash-Lite pricing: **$0.10/M input tokens, $0.40/M output tokens**

| Scenario | Single-stage augmented | Two-stage guard |
|----------|----------------------|-----------------|
| Junk scan | ~$0.000084 | ~$0.000032 |
| Food scan | ~$0.000308 | ~$0.000340 |
| 100 scans, 10% junk | **$0.02856** | $0.030920 (8% worse) |
| 100 scans, 40% junk | $0.022240 | **$0.019840** |

**Break-even:** Two-stage only wins if junk rate exceeds **38%**. Typical food tracking app: <10%.

**Actual value of single-stage augmented**: Not dramatic token savings — the key benefit is **cleaner rejection**: instead of Gemini hallucinating nutrition data for a laptop and failing the `has_food` check, it explicitly returns `is_food:false` and the system rejects early with a proper user-facing error.

---

## Agreed Design: Single-Stage Augmented

### Files to Change (4 files, 1 new method)

| File | Change |
|------|--------|
| `src/domain/services/prompts/system_prompts.py:159` | Add `"is_food": bool` as first field in `VISION_ANALYSIS` JSON schema + 1 instruction line |
| `src/domain/parsers/vision_response_models.py:25` | Add `is_food: bool = Field(True, ...)` to `VisionAnalyzeResponse` |
| `src/domain/parsers/gpt_response_parser.py:18` | Add `parse_is_food(response) → bool` method |
| `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:150` | Call `parse_is_food(result)` before `parse_to_nutrition` — raise `ValueError` if false |
| `src/app/handlers/command_handlers/scan_by_url_command_handler.py:103` | Same check |

### New Flow

```
image bytes
    │
    ▼
VisionAIService.analyze_with_strategy()   ← unchanged
    │
    ▼
Gemini Flash-Lite returns:
  { "is_food": false, "dish_name": null, "foods": [], ... }
    │
    ├── is_food=false → raise ValueError("Image does not appear to contain food")
    │                    ← NEW early exit, before parse_to_nutrition()
    └── is_food=true  → parse_to_nutrition() → existing has_food check (belt+suspenders)
```

### Explicitly NOT Changing
- `VisionAIService` — no new methods
- `AIModelManager` / `FALLBACK_CHAINS` — no new `ModelPurpose`
- `meal_analysis_strategy.py` — no new strategies
- `recognize_ingredient` flow — separate strategy/prompt, intentionally excluded
- PIL usage in `vision_ai_service.py` — already present, not a new dependency

### is_food Default Value
`Field(True)` — if Gemini fails to return the field (malformed response), default to True to avoid blocking legitimate food scans. The existing `has_food` check acts as a safety net.

---

## Success Criteria
- Non-food images (laptop, cat, shoe) → `ValueError("Image does not appear to contain food")` without running `parse_to_nutrition`
- Real food images → unchanged behavior, same nutrition output
- No regression on existing meal scan tests
- `is_food` field appears in `raw_gpt_json` for observability/debugging

---

## Unresolved Questions
None.
