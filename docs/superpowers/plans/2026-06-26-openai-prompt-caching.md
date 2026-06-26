# OpenAI Prompt Caching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OpenAI Responses API prompt-cache controls and telemetry so repeated long AI prompts can reuse provider-side prefix cache without changing user-facing behavior.

**Architecture:** Keep caching inside the infrastructure OpenAI provider boundary. Add one small prompt-cache policy helper, wire settings through `AIModelManager`, pass `prompt_cache_key`/optional `prompt_cache_retention` to Responses API calls, and record safe token metrics from OpenAI `usage`. Do not add Redis/application response caching and do not store prompts, images, or outputs.

**Tech Stack:** Python 3.13.2, FastAPI backend, OpenAI Python SDK `responses.create` / `responses.parse`, Pydantic settings, pytest, provider-neutral `src.observability`.

---

## Scope

In scope:
- OpenAI Responses API request kwargs: `prompt_cache_key`, optional `prompt_cache_retention`.
- Text and vision calls through `src/infra/services/ai/providers/openai_provider.py`.
- Low-cardinality metrics for `cached_tokens`, input tokens, and cache-hit request count.
- Tests proving kwargs are passed and no raw user content appears in cache keys or metrics.

Out of scope:
- Redis cache.
- Storing model outputs.
- Reworking prompt templates.
- Cloudflare Workers AI caching.
- Conversation `previous_response_id`.

## OpenAI Behavior To Respect

- Prompt caching is provider-side prefix caching, not response caching.
- Cache hits require prompts of at least 1024 tokens and matching initial prefix.
- `prompt_cache_key` is a routing hint. It must be stable for requests with the same reusable prefix and must not include raw user text.
- `prompt_cache_retention` can be unset, `in_memory`, or `24h` depending on model/org policy.
- Cache evidence comes from `response.usage.input_tokens_details.cached_tokens` on Responses API responses.

References:
- OpenAI Prompt Caching guide: `https://developers.openai.com/api/docs/guides/prompt-caching`
- OpenAI Responses API reference: `https://developers.openai.com/api/docs/api-reference/responses/create`

## File Map

- Create: `src/infra/services/ai/openai_prompt_cache_policy.py`
  - Responsibility: derive safe OpenAI prompt-cache kwargs from model, purpose, and system prompt.
- Create: `tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py`
  - Responsibility: unit-test key stability, disable behavior, retention validation, no raw prompt leakage.
- Modify: `src/infra/config/settings.py`
  - Responsibility: expose OpenAI prompt-cache settings.
- Modify: `src/infra/services/ai/ai_model_manager.py`
  - Responsibility: pass settings into `OpenAIProvider`.
- Modify: `src/infra/services/ai/providers/openai_provider.py`
  - Responsibility: include cache kwargs on all Responses API calls and emit usage metrics.
- Modify: `tests/unit/infra/services/ai/providers/test_openai_provider.py`
  - Responsibility: assert cache kwargs and usage metrics for text and vision calls.
- Modify: `tests/unit/infra/services/ai/test_ai_vision_failure_routing.py`
  - Responsibility: add fake settings fields so manager tests keep constructing cleanly.

## Design Notes

- Default `OPENAI_PROMPT_CACHE_ENABLED=true`: provider-side prompt caching is safe because OpenAI already controls eligibility and correctness. This only adds an explicit routing key.
- Default `OPENAI_PROMPT_CACHE_RETENTION=""`: do not force `24h` retention. Production can opt into `24h` after privacy/cost review.
- Key source: `model`, `purpose_hint`, and a SHA-256 digest of `system_message`. Do not hash user prompt by default because user prompts are often the variable suffix and would destroy key reuse.
- Key format: `mealtrack:{purpose}:{digest16}`. No raw prompt, no image data, no user ID.
- Metrics names:
  - `ai.openai.prompt_cache.request.count`
  - `ai.openai.prompt_cache.cached_tokens`
  - `ai.openai.prompt_cache.input_tokens`
- Metrics attributes:
  - `ai_provider=openai`
  - `ai_model=<model>`
  - `ai_purpose=<purpose or unknown>`
  - `cache_hit=true|false`

---

### Task 1: Add Prompt-Cache Policy Helper

**Files:**
- Create: `src/infra/services/ai/openai_prompt_cache_policy.py`
- Create: `tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py`

- [ ] **Step 1: Write failing tests for policy behavior**

Create `tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py`:

```python
import pytest

from src.infra.services.ai.openai_prompt_cache_policy import (
    OpenAIPromptCachePolicy,
)


def test_disabled_policy_returns_empty_kwargs():
    policy = OpenAIPromptCachePolicy(enabled=False)

    result = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="meal_scan",
        system_message="Return canonical meal JSON.",
    )

    assert result == {}


def test_enabled_policy_returns_stable_key_for_same_system_prompt():
    policy = OpenAIPromptCachePolicy(enabled=True, key_prefix="mealtrack")

    first = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="meal_scan",
        system_message="Return canonical meal JSON.",
    )
    second = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="meal_scan",
        system_message="Return canonical meal JSON.",
    )

    assert first == second
    assert first["prompt_cache_key"].startswith("mealtrack:meal_scan:")


def test_key_changes_when_model_or_system_prompt_changes():
    policy = OpenAIPromptCachePolicy(enabled=True, key_prefix="mealtrack")

    base = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="meal_scan",
        system_message="Return canonical meal JSON.",
    )
    other_model = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-18",
        purpose_hint="meal_scan",
        system_message="Return canonical meal JSON.",
    )
    other_system = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="meal_scan",
        system_message="Return canonical ingredient JSON.",
    )

    assert base["prompt_cache_key"] != other_model["prompt_cache_key"]
    assert base["prompt_cache_key"] != other_system["prompt_cache_key"]


def test_key_does_not_contain_raw_system_prompt():
    policy = OpenAIPromptCachePolicy(enabled=True, key_prefix="mealtrack")

    result = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="parse_text",
        system_message="secret patient meal instruction",
    )

    assert "secret" not in result["prompt_cache_key"]
    assert "patient" not in result["prompt_cache_key"]
    assert "instruction" not in result["prompt_cache_key"]


def test_retention_is_added_when_configured():
    policy = OpenAIPromptCachePolicy(
        enabled=True,
        key_prefix="mealtrack",
        retention="24h",
    )

    result = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="recipe",
        system_message="Return recipe JSON.",
    )

    assert result["prompt_cache_retention"] == "24h"


def test_invalid_retention_raises_value_error():
    with pytest.raises(ValueError, match="OPENAI_PROMPT_CACHE_RETENTION"):
        OpenAIPromptCachePolicy(enabled=True, retention="forever")
```

- [ ] **Step 2: Run the policy tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py -q
```

Expected:

```text
ERROR tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py
ModuleNotFoundError: No module named 'src.infra.services.ai.openai_prompt_cache_policy'
```

- [ ] **Step 3: Implement the policy helper**

Create `src/infra/services/ai/openai_prompt_cache_policy.py`:

```python
"""OpenAI prompt-cache request policy.

This module only builds provider-side prompt-cache request kwargs. It does not
cache responses and does not store raw prompts.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

_ALLOWED_RETENTION = {"in_memory", "24h"}
_SAFE_KEY_PART = re.compile(r"[^a-zA-Z0-9_-]+")


@dataclass(frozen=True)
class OpenAIPromptCachePolicy:
    """Build safe prompt-cache kwargs for OpenAI Responses API calls."""

    enabled: bool
    key_prefix: str = "mealtrack"
    retention: str | None = None

    def __post_init__(self) -> None:
        if self.retention and self.retention not in _ALLOWED_RETENTION:
            raise ValueError(
                "OPENAI_PROMPT_CACHE_RETENTION must be empty, 'in_memory', or '24h'"
            )

    def request_kwargs(
        self,
        *,
        model: str,
        purpose_hint: str | None,
        system_message: str | None,
    ) -> dict[str, Any]:
        """Return kwargs accepted by OpenAI Responses API methods."""
        if not self.enabled:
            return {}

        purpose = _safe_key_part(purpose_hint or "unknown")
        digest = hashlib.sha256(
            f"{model}\n{purpose}\n{system_message or ''}".encode("utf-8")
        ).hexdigest()[:16]
        kwargs: dict[str, Any] = {
            "prompt_cache_key": f"{_safe_key_part(self.key_prefix)}:{purpose}:{digest}"
        }
        if self.retention:
            kwargs["prompt_cache_retention"] = self.retention
        return kwargs


def _safe_key_part(value: str) -> str:
    safe = _SAFE_KEY_PART.sub("-", value.strip()).strip("-").lower()
    return safe or "unknown"
```

- [ ] **Step 4: Run the policy tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py -q
```

Expected:

```text
6 passed
```

- [ ] **Step 5: Commit Task 1**

```bash
git add src/infra/services/ai/openai_prompt_cache_policy.py \
  tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py
git commit -m "feat: add openai prompt cache policy"
```

---

### Task 2: Add Settings And Wire Provider Construction

**Files:**
- Modify: `src/infra/config/settings.py`
- Modify: `src/infra/services/ai/ai_model_manager.py`
- Modify: `tests/unit/infra/services/ai/test_ai_vision_failure_routing.py`
- Test: `tests/unit/infra/services/ai/test_ai_vision_failure_routing.py`

- [ ] **Step 1: Write a manager wiring test**

Append this test to `tests/unit/infra/services/ai/test_ai_vision_failure_routing.py`:

```python
def test_openai_provider_receives_prompt_cache_settings(mock_circuit_breaker):
    settings = _fake_settings()
    settings.OPENAI_PROMPT_CACHE_ENABLED = True
    settings.OPENAI_PROMPT_CACHE_RETENTION = "in_memory"
    settings.OPENAI_PROMPT_CACHE_KEY_PREFIX = "mealtrack-test"

    with patch("src.infra.services.ai.ai_model_manager.ProviderCircuitBreaker", return_value=mock_circuit_breaker):
        with patch("src.infra.services.ai.ai_model_manager.OpenAIProvider") as provider_cls:
            AIModelManager(settings=settings)

    provider_cls.assert_called_once()
    kwargs = provider_cls.call_args.kwargs
    assert kwargs["prompt_cache_enabled"] is True
    assert kwargs["prompt_cache_retention"] == "in_memory"
    assert kwargs["prompt_cache_key_prefix"] == "mealtrack-test"
```

- [ ] **Step 2: Run the manager test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/test_ai_vision_failure_routing.py::test_openai_provider_receives_prompt_cache_settings -q
```

Expected:

```text
KeyError: 'prompt_cache_enabled'
```

- [ ] **Step 3: Add settings fields**

In `src/infra/config/settings.py`, add these fields immediately after `OPENAI_STORE_RESPONSES`:

```python
    OPENAI_PROMPT_CACHE_ENABLED: bool = Field(
        default=True,
        description="Enable explicit OpenAI Responses API prompt cache routing.",
    )
    OPENAI_PROMPT_CACHE_RETENTION: str | None = Field(
        default="",
        description="Optional OpenAI prompt_cache_retention: empty, in_memory, or 24h.",
    )
    OPENAI_PROMPT_CACHE_KEY_PREFIX: str = Field(
        default="mealtrack",
        description="Safe prefix for OpenAI prompt_cache_key values.",
    )
```

- [ ] **Step 4: Update fake settings used by manager tests**

In `_fake_settings()` in `tests/unit/infra/services/ai/test_ai_vision_failure_routing.py`, add:

```python
    s.OPENAI_PROMPT_CACHE_ENABLED = True
    s.OPENAI_PROMPT_CACHE_RETENTION = ""
    s.OPENAI_PROMPT_CACHE_KEY_PREFIX = "mealtrack"
```

- [ ] **Step 5: Wire settings into `OpenAIProvider`**

In `src/infra/services/ai/ai_model_manager.py`, update the `OpenAIProvider(...)` construction:

```python
        openai = OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            request_timeout_seconds=settings.OPENAI_REQUEST_TIMEOUT_SECONDS,
            max_retries=settings.OPENAI_MAX_RETRIES,
            store_responses=settings.OPENAI_STORE_RESPONSES,
            prompt_cache_enabled=settings.OPENAI_PROMPT_CACHE_ENABLED,
            prompt_cache_retention=settings.OPENAI_PROMPT_CACHE_RETENTION or None,
            prompt_cache_key_prefix=settings.OPENAI_PROMPT_CACHE_KEY_PREFIX,
        )
```

- [ ] **Step 6: Run the manager tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/test_ai_vision_failure_routing.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 7: Commit Task 2**

```bash
git add src/infra/config/settings.py \
  src/infra/services/ai/ai_model_manager.py \
  tests/unit/infra/services/ai/test_ai_vision_failure_routing.py
git commit -m "feat: wire openai prompt cache settings"
```

---

### Task 3: Pass Cache Kwargs In OpenAI Provider

**Files:**
- Modify: `src/infra/services/ai/providers/openai_provider.py`
- Modify: `tests/unit/infra/services/ai/providers/test_openai_provider.py`
- Test: `tests/unit/infra/services/ai/providers/test_openai_provider.py`

- [ ] **Step 1: Update provider construction in existing tests**

In `tests/unit/infra/services/ai/providers/test_openai_provider.py`, add this helper near the top:

```python
def _provider(store_responses=False):
    return OpenAIProvider(
        api_key="test-key",
        request_timeout_seconds=20,
        max_retries=1,
        store_responses=store_responses,
        prompt_cache_enabled=True,
        prompt_cache_retention="in_memory",
        prompt_cache_key_prefix="mealtrack-test",
    )
```

Replace direct `OpenAIProvider(...)` construction in that file with `_provider(...)`.

- [ ] **Step 2: Add test for structured text cache kwargs**

Append:

```python
@pytest.mark.asyncio
async def test_generate_structured_text_includes_prompt_cache_kwargs():
    provider = _provider()
    parsed = _parsed_vision_response()
    provider._client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(output_parsed=parsed, usage=None)
    )

    await provider.generate(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Parse this meal text.",
        system_message="Return canonical meal text JSON.",
        schema=VisionNutritionResponse,
        purpose_hint="parse_text",
    )

    call_kwargs = provider._client.responses.parse.await_args.kwargs
    assert call_kwargs["prompt_cache_key"].startswith("mealtrack-test:parse_text:")
    assert call_kwargs["prompt_cache_retention"] == "in_memory"
```

- [ ] **Step 3: Add test for vision cache kwargs**

Append:

```python
@pytest.mark.asyncio
async def test_generate_with_vision_includes_prompt_cache_kwargs():
    provider = _provider()
    parsed = _parsed_vision_response()
    provider._client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(output_parsed=parsed, usage=None)
    )

    await provider.generate_with_vision(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Identify food.",
        image_data=b"image-bytes",
        system_message="Return canonical JSON.",
        schema=VisionNutritionResponse,
        image_mime_type="image/png",
        max_tokens=1500,
        purpose_hint="meal_scan",
    )

    call_kwargs = provider._client.responses.parse.await_args.kwargs
    assert call_kwargs["prompt_cache_key"].startswith("mealtrack-test:meal_scan:")
    assert call_kwargs["prompt_cache_retention"] == "in_memory"
```

- [ ] **Step 4: Run provider tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/providers/test_openai_provider.py -q
```

Expected:

```text
TypeError: OpenAIProvider.__init__() got an unexpected keyword argument 'prompt_cache_enabled'
```

- [ ] **Step 5: Update provider imports**

In `src/infra/services/ai/providers/openai_provider.py`, add:

```python
from src.infra.services.ai.openai_prompt_cache_policy import OpenAIPromptCachePolicy
```

- [ ] **Step 6: Update provider constructor**

Replace the constructor signature and body with:

```python
    def __init__(
        self,
        *,
        api_key: str,
        request_timeout_seconds: int,
        max_retries: int,
        store_responses: bool,
        prompt_cache_enabled: bool = True,
        prompt_cache_retention: str | None = None,
        prompt_cache_key_prefix: str = "mealtrack",
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=request_timeout_seconds,
            max_retries=max_retries,
        )
        self._store_responses = store_responses
        self._prompt_cache_policy = OpenAIPromptCachePolicy(
            enabled=prompt_cache_enabled,
            key_prefix=prompt_cache_key_prefix,
            retention=prompt_cache_retention,
        )
```

- [ ] **Step 7: Add helper method for cache kwargs**

Add this method inside `OpenAIProvider`:

```python
    def _prompt_cache_kwargs(
        self,
        *,
        model: str,
        system_message: str | None,
        purpose_hint: str | None,
    ) -> dict[str, Any]:
        return self._prompt_cache_policy.request_kwargs(
            model=model,
            purpose_hint=purpose_hint,
            system_message=system_message,
        )
```

- [ ] **Step 8: Pass cache kwargs to structured text calls**

In `generate()`, before the `if schema is not None:` branch, add:

```python
        purpose_hint = kwargs.get("purpose_hint")
        prompt_cache_kwargs = self._prompt_cache_kwargs(
            model=model,
            system_message=system_message,
            purpose_hint=purpose_hint,
        )
```

Then add `**prompt_cache_kwargs,` to both `responses.parse(...)` and `responses.create(...)` calls:

```python
                store=self._store_responses,
                **prompt_cache_kwargs,
```

and:

```python
            store=self._store_responses,
            **prompt_cache_kwargs,
```

- [ ] **Step 9: Pass cache kwargs to vision calls**

In `generate_with_vision()`, before `response = await self._client.responses.parse(...)`, add:

```python
        purpose_hint = kwargs.get("purpose_hint")
        prompt_cache_kwargs = self._prompt_cache_kwargs(
            model=model,
            system_message=system_message,
            purpose_hint=purpose_hint,
        )
```

Then add `**prompt_cache_kwargs,` to the vision `responses.parse(...)` call:

```python
            store=self._store_responses,
            **prompt_cache_kwargs,
```

- [ ] **Step 10: Run provider tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/providers/test_openai_provider.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 11: Commit Task 3**

```bash
git add src/infra/services/ai/providers/openai_provider.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py
git commit -m "feat: send openai prompt cache kwargs"
```

---

### Task 4: Record Prompt-Cache Usage Metrics

**Files:**
- Modify: `src/infra/services/ai/providers/openai_provider.py`
- Modify: `tests/unit/infra/services/ai/providers/test_openai_provider.py`
- Test: `tests/unit/infra/services/ai/providers/test_openai_provider.py`

- [ ] **Step 1: Add metric test for cached token usage**

Append to `tests/unit/infra/services/ai/providers/test_openai_provider.py`:

```python
@pytest.mark.asyncio
async def test_records_prompt_cache_usage_metrics(monkeypatch):
    provider = _provider()
    parsed = _parsed_vision_response()
    usage = SimpleNamespace(
        input_tokens=1500,
        input_tokens_details=SimpleNamespace(cached_tokens=1024),
    )
    provider._client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(output_parsed=parsed, usage=usage)
    )
    metrics = []

    def capture_metric(name, value=1.0, *, unit=None, attributes=None):
        metrics.append(
            {
                "name": name,
                "value": value,
                "unit": unit,
                "attributes": attributes or {},
            }
        )

    monkeypatch.setattr(
        "src.infra.services.ai.providers.openai_provider.increment_metric",
        capture_metric,
    )

    await provider.generate(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Parse this meal text.",
        system_message="Return canonical meal text JSON.",
        schema=VisionNutritionResponse,
        purpose_hint="parse_text",
    )

    assert {
        "name": "ai.openai.prompt_cache.request.count",
        "value": 1.0,
        "unit": None,
        "attributes": {
            "ai_provider": "openai",
            "ai_model": "gpt-5.4-mini-2026-03-17",
            "ai_purpose": "parse_text",
            "cache_hit": "true",
        },
    } in metrics
    assert any(
        metric["name"] == "ai.openai.prompt_cache.cached_tokens"
        and metric["value"] == 1024
        and metric["unit"] == "token"
        for metric in metrics
    )
    assert any(
        metric["name"] == "ai.openai.prompt_cache.input_tokens"
        and metric["value"] == 1500
        and metric["unit"] == "token"
        for metric in metrics
    )
```

- [ ] **Step 2: Run metric test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/providers/test_openai_provider.py::test_records_prompt_cache_usage_metrics -q
```

Expected:

```text
AttributeError: module 'src.infra.services.ai.providers.openai_provider' has no attribute 'increment_metric'
```

- [ ] **Step 3: Import metric facade**

In `src/infra/services/ai/providers/openai_provider.py`, add:

```python
from src.observability import increment_metric
```

- [ ] **Step 4: Add usage extraction helpers**

Add these methods inside `OpenAIProvider`:

```python
    def _record_prompt_cache_usage(
        self,
        response: Any,
        *,
        model: str,
        purpose_hint: str | None,
    ) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        input_tokens = _usage_number(usage, "input_tokens")
        details = getattr(usage, "input_tokens_details", None)
        cached_tokens = _usage_number(details, "cached_tokens") if details else 0
        attributes = {
            "ai_provider": "openai",
            "ai_model": model,
            "ai_purpose": purpose_hint or "unknown",
            "cache_hit": "true" if cached_tokens > 0 else "false",
        }
        increment_metric(
            "ai.openai.prompt_cache.request.count",
            attributes=attributes,
        )
        increment_metric(
            "ai.openai.prompt_cache.cached_tokens",
            cached_tokens,
            unit="token",
            attributes=attributes,
        )
        if input_tokens > 0:
            increment_metric(
                "ai.openai.prompt_cache.input_tokens",
                input_tokens,
                unit="token",
                attributes=attributes,
            )
```

Add this module-level helper below the class:

```python
def _usage_number(obj: Any, attr: str) -> float:
    value = getattr(obj, attr, 0)
    if value is None:
        return 0
    return float(value)
```

- [ ] **Step 5: Call metric helper after each OpenAI response**

In the structured `responses.parse(...)` branch in `generate()`, add immediately after the awaited call:

```python
            self._record_prompt_cache_usage(
                response,
                model=model,
                purpose_hint=purpose_hint,
            )
```

In the non-schema `responses.create(...)` branch in `generate()`, add immediately after the awaited call:

```python
        self._record_prompt_cache_usage(
            response,
            model=model,
            purpose_hint=purpose_hint,
        )
```

In `generate_with_vision()`, add immediately after the awaited `responses.parse(...)` call:

```python
        self._record_prompt_cache_usage(
            response,
            model=model,
            purpose_hint=purpose_hint,
        )
```

- [ ] **Step 6: Run provider tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/providers/test_openai_provider.py -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 7: Commit Task 4**

```bash
git add src/infra/services/ai/providers/openai_provider.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py
git commit -m "feat: record openai prompt cache metrics"
```

---

### Task 5: Regression Sweep And Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/external-services.md` if present, otherwise skip this file and only update `README.md`
- Test: focused AI unit suites

- [ ] **Step 1: Document runtime env vars in README**

In `README.md`, under the AI or environment section, add:

```markdown
### OpenAI prompt caching

OpenAI Responses API calls use provider-side prompt-cache routing by default.
This is not an application response cache.

Environment variables:

| Variable | Default | Purpose |
|---|---:|---|
| `OPENAI_PROMPT_CACHE_ENABLED` | `true` | Sends `prompt_cache_key` on OpenAI Responses API calls. |
| `OPENAI_PROMPT_CACHE_RETENTION` | empty | Optional retention policy: empty, `in_memory`, or `24h`. |
| `OPENAI_PROMPT_CACHE_KEY_PREFIX` | `mealtrack` | Safe prefix for generated cache keys. |

Operational proof comes from Sentry metrics:
- `ai.openai.prompt_cache.request.count`
- `ai.openai.prompt_cache.cached_tokens`
- `ai.openai.prompt_cache.input_tokens`

Do not log prompt text, image bytes, or raw model responses while debugging cache behavior.
```

- [ ] **Step 2: Update external services docs if the file exists**

If `docs/external-services.md` exists, add:

```markdown
## OpenAI Responses API Prompt Caching

MealTrack sends `prompt_cache_key` for OpenAI Responses API calls through
`OpenAIProvider`. The key is derived from model, purpose, and system prompt hash.
It never contains raw user prompt text, images, emails, or IDs.

Prompt caching is best-effort and only shows benefit for 1024+ token requests
with matching prefixes. Monitor `cached_tokens` metrics before declaring a cost
win.
```

- [ ] **Step 3: Run policy and provider tests**

Run:

```bash
.venv/bin/python -m pytest \
  tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py \
  -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 4: Run AI regression tests**

Run:

```bash
.venv/bin/python -m pytest \
  tests/unit/infra/services/ai \
  tests/unit/infra/adapters/test_vision_ai_service.py \
  tests/unit/infra/adapters/test_vision_ai_service_resilience.py \
  tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py \
  -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 5: Run lint for touched files**

Run:

```bash
.venv/bin/python -m ruff check \
  src/infra/services/ai/openai_prompt_cache_policy.py \
  src/infra/services/ai/providers/openai_provider.py \
  src/infra/services/ai/ai_model_manager.py \
  src/infra/config/settings.py \
  tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py \
  tests/unit/infra/services/ai/test_ai_vision_failure_routing.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 6: Commit Task 5**

```bash
git add README.md docs/external-services.md 2>/dev/null || git add README.md
git commit -m "docs: document openai prompt caching"
```

---

## Final Verification

- [ ] Run the original collection-sensitive set:

```bash
.venv/bin/python -m pytest \
  tests/unit/api/routes/test_movement_routes.py \
  tests/unit/api/test_auth.py \
  tests/unit/api/test_base_dependencies.py \
  tests/unit/api/test_feature_flags_routes.py \
  tests/unit/api/test_health_router.py \
  tests/unit/api/test_meal_suggestions_routes.py \
  tests/unit/api/test_premium_middleware.py \
  tests/unit/api/test_small_v1_routers.py \
  tests/unit/domain/test_feature_flags.py \
  tests/unit/infra/adapters/test_meal_generation_service_resilience.py \
  tests/unit/infra/adapters/test_vision_ai_service.py \
  tests/unit/infra/adapters/test_vision_ai_service_resilience.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py \
  tests/unit/infra/services/ai/test_ai_vision_failure_routing.py \
  -q
```

Expected:

```text
all selected tests pass
```

- [ ] Run full unit suite before push:

```bash
.venv/bin/python -m pytest tests/unit -q
```

Expected:

```text
all selected tests pass
```

- [ ] Push normally and let the local pre-push hook run:

```bash
git push
```

Expected:

```text
✅ All tests passed. Pushing...
```

## Red-Team Review

| Finding | Severity | Plan response |
|---|---:|---|
| Cache key includes raw user prompt or image data | High | Key uses only model, purpose, and system prompt hash. Tests assert raw words do not appear. |
| Explicit `24h` retention violates org privacy expectations | High | Default retention is empty. `24h` is opt-in via env. |
| Cache metrics leak content via attributes | High | Attributes are provider, model, purpose, and boolean hit flag only. |
| Prompt cache has no effect for short prompts | Medium | Plan records input/cached token metrics and docs state 1024+ token threshold. |
| Hashing only system prompt routes too many unrelated calls together | Medium | Purpose and model are included. Actual OpenAI prefix still must match for cache hit. |
| Provider constructor change breaks tests with mocks | Medium | Task 2 updates fake settings; Task 3 updates provider tests. |
| Metrics throw when mocked response lacks `usage` | Medium | `_record_prompt_cache_usage` returns when usage is absent. |

## Self-Review

Spec coverage:
- Prompt-cache request params: Task 3.
- Settings: Task 2.
- Metrics: Task 4.
- Tests-first execution: every implementation task starts with failing tests.
- Docs: Task 5.
- Privacy: Task 1 tests and Red-Team Review.

Placeholder scan:
- No deferred implementation markers.
- No undefined helper names after Task 1.
- No raw prompt logging or storage.

Type consistency:
- `OpenAIPromptCachePolicy.request_kwargs(...)` signature is used consistently in tests and provider.
- `prompt_cache_enabled`, `prompt_cache_retention`, and `prompt_cache_key_prefix` are used consistently from settings to provider.
- Metrics helper uses existing `increment_metric(name, value=1.0, unit=None, attributes=None)` signature.

## Execution Handoff

Plan complete. Use one of:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.
