---
phase: 3
title: "Observability and Validation"
status: pending
priority: P2
effort: "2h"
dependencies: [1, 2]
---

# Phase 3: Observability and Validation

## Overview

Validate that gateway routing is live, confirm CF dashboard shows analytics, write targeted tests, and update env docs. No new instrumentation code needed — CF AI Gateway logs request metadata (model, token counts, cost, latency, status) automatically once `cf-aig-gateway-id` is present.

## Related Code Files

- Read: `src/infra/services/ai/ai_model_manager.py` — confirm `purpose_hint` forwarded
- Write: `tests/unit/infra/services/ai/test_cloudflare_workers_ai_vision_gateway.py` — Workers AI gateway header tests
- Write: `tests/unit/infra/services/ai/test_gemini_provider_gateway.py` — Gemini gateway client tests
- Write: `.env.example` — document new `CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED`
- Write: `docs/external-services.md` — CF AI Gateway section

## Implementation Steps

### Step 1 — Confirm `purpose_hint` forwarding (already present — read-only check)

`ai_model_manager.py:362` already has `purpose_hint=purpose.value` (marked `# NEW`). No code change needed. Run: `grep -n "purpose_hint" src/infra/services/ai/ai_model_manager.py` to confirm the line exists before running tests.

### Step 2 — Unit tests for Workers AI vision gateway headers

`tests/unit/infra/services/ai/test_cloudflare_workers_ai_vision_gateway.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.infra.services.ai.providers.cloudflare_workers_ai_provider import CloudflareWorkersAIProvider

def _make_provider(gateway_id: str) -> CloudflareWorkersAIProvider:
    # Verify self._gateway_id is stored (would AttributeError if missing)
    p = CloudflareWorkersAIProvider(
        account_id="acct", api_token="tok", text_model="m",
        gateway_id=gateway_id, vision_enabled=True, vision_model="vm",
    )
    assert p._gateway_id == gateway_id  # explicit guard from red-team Finding 1
    return p

def _make_httpx_mock(captured_headers: dict):
    """
    Build an AsyncClient context manager mock with AsyncMock for __aenter__/__aexit__.
    httpx.AsyncClient is used as `async with AsyncClient() as client:` — __aenter__
    must be a coroutine or TypeError is raised on 'await' expression.
    """
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"result": {"response": '{"foods":[],"is_food":false}'}}

    async def fake_post(url, json, headers):
        captured_headers.update(headers)
        return mock_resp

    mock_inner = MagicMock()
    mock_inner.post = AsyncMock(side_effect=fake_post)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_inner)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_client_cls = MagicMock(return_value=mock_cm)
    return mock_client_cls

@pytest.mark.asyncio
async def test_gateway_headers_injected_when_gateway_id_set():
    provider = _make_provider("gw-123")
    captured_headers: dict = {}

    with patch("src.infra.services.ai.providers.cloudflare_workers_ai_provider.httpx.AsyncClient",
               _make_httpx_mock(captured_headers)):
        await provider._post_workers_ai("vm", {}, purpose="meal_scan")

    assert captured_headers["cf-aig-gateway-id"] == "gw-123"
    assert captured_headers["cf-aig-skip-cache"] == "true"
    assert captured_headers["cf-aig-collect-log-payload"] == "false"
    assert json.loads(captured_headers["cf-aig-metadata"]) == {"purpose": "meal_scan"}

@pytest.mark.asyncio
async def test_no_gateway_headers_when_gateway_id_empty():
    provider = _make_provider("")
    captured_headers: dict = {}

    with patch("src.infra.services.ai.providers.cloudflare_workers_ai_provider.httpx.AsyncClient",
               _make_httpx_mock(captured_headers)):
        await provider._post_workers_ai("vm", {}, purpose="meal_scan")

    assert "cf-aig-gateway-id" not in captured_headers
    assert "cf-aig-skip-cache" not in captured_headers
```

### Step 3 — Unit tests for Gemini gateway client

`tests/unit/infra/services/ai/test_gemini_provider_gateway.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

# DO NOT use importlib.reload — it pollutes singleton state across tests.
# GeminiModelManager singleton survives reload and causes flaky cross-test contamination.
# Pattern: mock both GeminiModelManager.get_instance and get_settings before
# instantiating GeminiProvider() directly inside the patch context.

_MODULE = "src.infra.services.ai.providers.gemini_provider"
_MANAGER = "src.infra.services.ai.gemini_model_manager.GeminiModelManager.get_instance"

def _enabled_settings():
    s = MagicMock()
    s.CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED = True
    s.CLOUDFLARE_ACCOUNT_ID = "acct"
    s.CLOUDFLARE_AI_GATEWAY_ID = "gw"
    s.GOOGLE_API_KEY = "gkey"
    return s

def test_gateway_client_built_when_setting_enabled():
    from src.infra.services.ai.providers.gemini_provider import GeminiProvider
    with patch(f"{_MODULE}.get_settings", return_value=_enabled_settings()):
        with patch(_MANAGER, return_value=MagicMock()):
            with patch(f"{_MODULE}.genai.Client") as mock_client:
                provider = GeminiProvider()
                assert provider._gateway_client is not None
                mock_client.assert_called_once()
                # Verify base_url contains the expected gateway URL pattern
                call_kwargs = mock_client.call_args.kwargs
                http_opts = call_kwargs.get("http_options")
                assert "gateway.ai.cloudflare.com" in str(http_opts)

def test_gateway_client_none_when_setting_disabled():
    from src.infra.services.ai.providers.gemini_provider import GeminiProvider
    s = MagicMock()
    s.CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED = False
    with patch(f"{_MODULE}.get_settings", return_value=s):
        with patch(_MANAGER, return_value=MagicMock()):
            provider = GeminiProvider()
            assert provider._gateway_client is None

def test_gateway_client_none_when_credentials_missing():
    from src.infra.services.ai.providers.gemini_provider import GeminiProvider
    s = MagicMock()
    s.CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED = True
    s.CLOUDFLARE_ACCOUNT_ID = ""  # missing
    s.CLOUDFLARE_AI_GATEWAY_ID = "gw"
    s.GOOGLE_API_KEY = "gkey"
    with patch(f"{_MODULE}.get_settings", return_value=s):
        with patch(_MANAGER, return_value=MagicMock()):
            provider = GeminiProvider()
            assert provider._gateway_client is None  # logs WARNING, returns None
```

### Step 4 — Update `.env.example`

Add near existing `CLOUDFLARE_WORKERS_AI_VISION_*` block:

```bash
# Cloudflare AI Gateway — Gemini vision routing
# Routes Gemini vision calls through CF AI Gateway for analytics/cost tracking
# Requires CLOUDFLARE_AI_GATEWAY_ID and CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED=false
```

### Step 5 — Update `docs/external-services.md`

Add CF AI Gateway subsection under the Cloudflare entry:

```markdown
### Cloudflare AI Gateway

Vision calls for both Workers AI and Gemini route through [Cloudflare AI Gateway](https://developers.cloudflare.com/ai-gateway/)
when `CLOUDFLARE_AI_GATEWAY_ID` is set (Workers AI) or
`CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED=true` (Gemini).

Dashboard: https://dash.cloudflare.com → AI Gateway → {gateway_id}

Privacy: `cf-aig-collect-log-payload: false` is sent on every call — no food images,
prompts, or AI responses are stored in CF logs. Request metadata only (model, tokens, latency, cost).

Cache: disabled for vision (`cf-aig-skip-cache: true`). Images are always unique; caching adds
overhead with zero hit rate.
```

### Step 6 — Manual smoke test checklist

Run against staging with real `CLOUDFLARE_AI_GATEWAY_ID`:

- [ ] Trigger a meal scan → check CF dashboard shows 1 new Workers AI request with `purpose=meal_scan` metadata
- [ ] Trigger an ingredient scan → check CF dashboard shows 1 new Workers AI request — **known limitation**: metadata will show `purpose=meal_scan` (not `ingredient_scan`) because `VisionAIService.analyze_with_strategy()` and `_analyze_without_nutrition_contract()` both hardcode `purpose=ModelPurpose.MEAL_SCAN` (`vision_ai_service.py:107,165`). This is a pre-existing issue outside the scope of this plan.
- [ ] Enable `CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED=true` → trigger scan → verify gateway dashboard shows Google AI Studio request
- [ ] Check "Log payload" column is empty for all vision entries (privacy guard working)
- [ ] Force a gateway error (invalid gateway ID) → confirm scan still succeeds via Gemini fallback

## Success Criteria

- [ ] `purpose_hint=purpose.value` confirmed in `AIModelManager.generate_with_vision()` call to provider
- [ ] Workers AI gateway header unit tests pass
- [ ] Gemini gateway client unit tests pass
- [ ] `.env.example` documents `CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED`
- [ ] `docs/external-services.md` has CF AI Gateway section
- [ ] `pytest tests/unit/infra/services/ai/` passes (all AI provider tests green)

## Unresolved Questions

1. Is `gemini-3.1-flash-lite` a valid Google AI Studio model ID? Not found in Google's public model list. If invalid, remove from `FALLBACK_CHAINS[ModelPurpose.MEAL_SCAN]` and replace with `gemini-2.5-flash-lite`.
2. CF AI Gateway latency overhead for Gemini vision: ~10–50ms (Cloudflare estimate). Acceptable for 1–15s vision calls, but worth benchmarking in staging on first deployment.
