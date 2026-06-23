---
phase: 2
title: "Gemini Vision Gateway"
status: pending
priority: P1
effort: "4h"
dependencies: [1]
---

# Phase 2: Gemini Vision Gateway

## Overview

Route Gemini vision calls through CF AI Gateway using `google-genai` SDK's native `HttpOptions(base_url=...)`. LangChain's `ChatGoogleGenerativeAI` has an unfixed bug preventing custom base URLs — the SDK path is the only viable option.

**Constraint**: Gemini text calls that resolve a `cached_content` name must NOT be routed through CF AI Gateway. Context cache objects are Google-side infrastructure; proxying breaks them. Only `generate_with_vision()` (no `cached_content`) is in scope here.

## Architecture

```
CF AI Gateway URL for Gemini:
https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/google-ai-studio

genai.Client(
    api_key=GOOGLE_API_KEY,
    http_options=HttpOptions(
        base_url="https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/google-ai-studio",
        headers={
            "cf-aig-skip-cache": "true",
            "cf-aig-collect-log-payload": "false",
        }
    )
)
```

Flow in `GeminiProvider.generate_with_vision()`:
1. If `CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED=true` and gateway ID set → use `genai.Client` gateway path
2. Try structured output via `client.models.generate_content()` with `VisionAnalyzeResponse` schema
3. On failure → fall back to existing LangChain structured output path (current behavior)
4. On LangChain failure → raw text parse (current behavior)

## Related Code Files

- Modify: `src/infra/config/settings.py`
  - Add `CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED: bool`
- Modify: `src/infra/services/ai/providers/gemini_provider.py`
  - `__init__`: conditionally build `genai.Client` with gateway `HttpOptions`
  - `generate_with_vision()`: try gateway client first when enabled, fall through to LangChain
- Read-only: `src/infra/services/ai/gemini_cache_manager.py` (pattern reference for `genai.Client`)
- Read-only: `src/infra/services/ai/ai_model_manager.py` (verify `purpose_hint` forwarding)

## Implementation Steps

### Step 1 — Add setting

In `src/infra/config/settings.py`, near the other `CLOUDFLARE_*` fields:

```python
CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED: bool = Field(
    default=False,
    description=(
        "Route Gemini vision calls through Cloudflare AI Gateway. "
        "Requires CLOUDFLARE_AI_GATEWAY_ID and CLOUDFLARE_ACCOUNT_ID to be set."
    ),
)
```

### Step 2 — Build gateway `genai.Client` in `GeminiProvider.__init__`

```python
from google import genai
from google.genai.types import HttpOptions

class GeminiProvider(AIProviderPort):
    def __init__(self) -> None:
        self._model_manager = GeminiModelManager.get_instance()
        self._gateway_client: genai.Client | None = self._build_gateway_client()

    def _build_gateway_client(self) -> "genai.Client | None":
        from src.infra.config.settings import get_settings
        settings = get_settings()

        if not getattr(settings, "CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED", False):
            return None
        account_id = getattr(settings, "CLOUDFLARE_ACCOUNT_ID", "")
        gateway_id = getattr(settings, "CLOUDFLARE_AI_GATEWAY_ID", "")
        api_key = getattr(settings, "GOOGLE_API_KEY", "") or ""
        if not (account_id and gateway_id and api_key):
            logger.warning(
                "[GEMINI-GATEWAY] CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED=true "
                "but account_id/gateway_id/api_key missing — gateway client disabled"
            )
            return None

        base_url = (
            f"https://gateway.ai.cloudflare.com/v1"
            f"/{account_id}/{gateway_id}/google-ai-studio"
        )
        return genai.Client(
            api_key=api_key,
            http_options=HttpOptions(
                base_url=base_url,
                headers={
                    "cf-aig-skip-cache": "true",
                    "cf-aig-collect-log-payload": "false",
                },
            ),
        )
```

### Step 3 — Add gateway vision call helper

```python
async def _generate_vision_via_gateway(
    self,
    model: str,
    prompt: str,
    image_data: bytes,
    system_message: str | None,
    max_tokens: int,
    purpose_hint: str,
) -> dict[str, Any]:
    """Call Gemini vision through CF AI Gateway using google-genai SDK."""
    from google.genai import types as genai_types
    from src.domain.parsers.vision_response_models import VisionAnalyzeResponse

    parts = []
    if system_message:
        parts.append(genai_types.Part.from_text(text=system_message))
    parts.append(genai_types.Part.from_text(text=prompt))
    parts.append(genai_types.Part.from_bytes(data=image_data, mime_type="image/jpeg"))

    config = genai_types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=VisionAnalyzeResponse,
    )

    # Use async API directly — do NOT use asyncio.to_thread(client.models.generate_content, ...)
    # google-genai SDK's .aio namespace provides native async calls;
    # wrapping the sync method in to_thread risks RuntimeError if SDK uses async internals.
    response = await self._gateway_client.aio.models.generate_content(
        model=model,
        contents=[genai_types.Content(role="user", parts=parts)],
        config=config,
    )

    text = response.text
    if not text or not text.strip():
        raise ValueError(f"[GEMINI-GATEWAY-VISION] Empty response for model={model}")

    parsed = self._extract_json(text)
    validated = VisionAnalyzeResponse.model_validate(parsed)
    return validated.model_dump()
```

### Step 4 — Integrate into `generate_with_vision()`

Wrap the new gateway attempt at the top of the existing method:

```python
async def generate_with_vision(self, model, prompt, image_data, system_message=None, **kwargs):
    purpose_hint: str = kwargs.get("purpose_hint", "")
    max_tokens: int = kwargs.get("max_tokens", 4096)

    # Try CF AI Gateway path first when configured
    if self._gateway_client is not None:
        try:
            return await self._generate_vision_via_gateway(
                model=model,
                prompt=prompt,
                image_data=image_data,
                system_message=system_message,
                max_tokens=max_tokens,
                purpose_hint=purpose_hint,
            )
        except Exception as exc:
            # WARNING level — a gateway failure may have transmitted data before erroring.
            # Include exc string for observability. DO NOT swallow silently at DEBUG.
            logger.warning("[GEMINI-GATEWAY-VISION-FALLBACK] model=%s error=%s", model, exc)
            increment_metric("ai.vision.gateway.fallback.count", tags={"provider": "gemini", "model": model})
            # Fall through to LangChain path below

    # Existing LangChain structured output path (unchanged)
    ...
```

### Step 5 — Verify `gemini-3.1-flash-lite` model ID

During testing, attempt a vision call using `gemini-3.1-flash-lite` through the gateway. If Google returns a 404/invalid-model error, this model needs to be removed from `FALLBACK_CHAINS[ModelPurpose.MEAL_SCAN]` and replaced with `gemini-2.5-flash-lite`. Update `ai_model_manager.py` if needed.

### Step 6 — Never call `client.models.list()`

The `genai.Client` through CF AI Gateway has a known bug: `client.models.list()` fails (HTTP 500, error 2002). This is already avoided — `GeminiProvider.get_available_models()` returns a hardcoded list. Ensure the new gateway client is never passed to any `list()` call.

## Success Criteria

- [ ] `CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED` field in `Settings`
- [ ] `GeminiProvider._gateway_client` is `None` when setting is `false` (default)
- [ ] Gemini vision calls route through CF AI Gateway URL when enabled
- [ ] `cf-aig-skip-cache: true` and `cf-aig-collect-log-payload: false` sent with every gateway call
- [ ] On gateway exception, falls back to existing LangChain path without re-raising
- [ ] Gemini text `generate()` method is NOT touched — no gateway routing for text
- [ ] Existing structured output and raw-parse fallback behavior preserved
- [ ] Unit tests pass for both gateway-enabled and gateway-disabled cases

## Risk Assessment

- **`genai.Client` not thread-safe?** — `GeminiCacheManager` already uses this pattern via `asyncio.to_thread`. Same approach used here.
- **`gemini-3.1-flash-lite` invalid model**: surfaces as Google 404 → `_generate_vision_via_gateway` raises → falls back to LangChain path. Non-breaking.
- **Gateway latency overhead**: ~10–50ms per Cloudflare estimate, negligible vs 1–15s Gemini inference time.
- **`HttpOptions` header merging**: `cf-aig-*` headers set at client level; individual calls can still pass request-level headers. No conflict with `x-goog-api-key` (managed by SDK).
- **`google-genai` SDK `HttpOptions` `base_url` bug**: `client.models.list()` fails through gateway (known bug) — not called here. `generate_content` works correctly.
