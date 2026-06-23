---
phase: 1
title: "Workers AI Vision Gateway"
status: pending
priority: P1
effort: "2h"
dependencies: []
---

# Phase 1: Workers AI Vision Gateway

## Overview

Route Workers AI vision REST calls through Cloudflare AI Gateway by injecting `cf-aig-gateway-id` into the existing `_post_workers_ai()` httpx call. The `gateway_id` is already stored in `CloudflareWorkersAIProvider.__init__` (used by LangChain text path) but not threaded into the REST vision path.

## Architecture

**Pattern B (CF recommended):** Keep existing URL `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}`. Add one header: `cf-aig-gateway-id: {gateway_id}`.

```
Before: [vision REST] → api.cloudflare.com (direct)
After:  [vision REST] → api.cloudflare.com → [CF AI Gateway routes internally]
```

Additional headers for all vision calls:
- `cf-aig-skip-cache: true` — images are always unique, no cache value
- `cf-aig-collect-log-payload: false` — no food image bytes/prompts stored in CF logs
- `cf-aig-metadata: {"purpose": "{purpose_hint}"}` — per-purpose analytics in dashboard

## Related Code Files

- Modify: `src/infra/services/ai/providers/cloudflare_workers_ai_provider.py`
  - `__init__`: store `gateway_id` in `self._gateway_id` (currently used only by LangChain, not REST)
  - `_post_workers_ai()`: inject gateway headers when `self._gateway_id` is set
  - `generate_with_vision()`: pass `purpose_hint` through to `_post_workers_ai()`

## Implementation Steps

1. **Add `self._gateway_id` to `__init__`** (new — does NOT currently exist)
   ```python
   # Currently __init__ consumes gateway_id only for ChatCloudflareWorkersAI kwargs
   # (line 53-54: kwargs["ai_gateway"] = gateway_id) and never stores it.
   # Add this assignment before the kwargs block:
   self._gateway_id = gateway_id  # used by _gateway_headers() for REST vision path
   ```
   **Verify**: add `assert provider._gateway_id == "fake_gateway"` to the first test in `TestGatewayConfig` to catch `AttributeError` before it reaches the circuit breaker.

2. **Build gateway headers helper** (inside `CloudflareWorkersAIProvider`):
   ```python
   def _gateway_headers(self, purpose: str = "") -> dict[str, str]:
       """Headers to route this call through CF AI Gateway."""
       if not self._gateway_id:
           return {}
       headers: dict[str, str] = {
           "cf-aig-gateway-id": self._gateway_id,
           "cf-aig-skip-cache": "true",
           "cf-aig-collect-log-payload": "false",
       }
       if purpose:
           import json
           headers["cf-aig-metadata"] = json.dumps({"purpose": purpose})
       return headers
   ```

3. **Update `_post_workers_ai()` signature** to accept `purpose`:
   ```python
   async def _post_workers_ai(self, model: str, payload: dict, purpose: str = "") -> dict:
       url = _CF_REST_BASE.format(account_id=self._account_id, model=model)
       headers = {
           "Authorization": f"Bearer {self._api_token}",
           "Content-Type": "application/json",
           **self._gateway_headers(purpose),
       }
       async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
           resp = await client.post(url, json=payload, headers=headers)
           resp.raise_for_status()
           return resp.json()
   ```

4. **Pass `purpose_hint` from `generate_with_vision()` to `_post_workers_ai()`**:
   ```python
   async def generate_with_vision(self, model, prompt, image_data, system_message=None, **kwargs):
       purpose_hint: str = kwargs.get("purpose_hint", "")
       ...
       raw = await self._post_workers_ai(model, payload, purpose=purpose_hint)
   ```

5. **`purpose_hint` forwarding confirmed — no action needed**
   `ai_model_manager.py:362` already has `purpose_hint=purpose.value` as an explicit kwarg (marked `# NEW`). Do not add it again. Verify with: `grep -n "purpose_hint" src/infra/services/ai/ai_model_manager.py`.

6. **Guard**: When `self._gateway_id` is empty string, `_gateway_headers()` returns `{}` — no headers added, behavior identical to current. Gateway routing is always opt-in.

## Success Criteria

- [ ] `_post_workers_ai()` includes `cf-aig-gateway-id` header when `CLOUDFLARE_AI_GATEWAY_ID` is set
- [ ] `cf-aig-skip-cache: true` present on all Workers AI vision calls
- [ ] `cf-aig-collect-log-payload: false` present on all Workers AI vision calls
- [ ] `cf-aig-metadata: {"purpose": "meal_scan"}` present on vision calls with purpose hint
- [ ] When `CLOUDFLARE_AI_GATEWAY_ID` is empty, headers not added (backward compat)
- [ ] Existing unit tests for `CloudflareWorkersAIProvider` pass without changes
- [ ] No changes to `FALLBACK_CHAINS`, circuit breaker, or `VisionAIService`

## Risk Assessment

- **Low risk**: Pattern B is additive — one extra header. If gateway is misconfigured, Workers AI returns an error that the existing `AIVisionError`/fallback chain handles.
- **Token leak**: `cf-aig-api-token` is the same token already in `Authorization` — no new secret surface.
- **Gateway not enabled in Cloudflare dashboard**: returns HTTP 400 with `cf-aig-gateway-id not found`. This surfaces as `httpx.HTTPStatusError` → caught by `AIVisionError(kind=provider_error)` → fallback to Gemini.
