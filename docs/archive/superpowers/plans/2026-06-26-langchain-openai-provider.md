# LangChain OpenAI Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace MealTrack's raw OpenAI SDK request path with LangChain's `ChatOpenAI` integration while preserving the existing `AIProviderPort`, OpenAI prompt caching, structured output, vision, metrics, and fallback behavior.

**Architecture:** Keep the domain and application layers unchanged. Add a thin infrastructure adapter around LangChain's `ChatOpenAI` so `OpenAIProvider` still exposes the same provider port methods but no longer calls `AsyncOpenAI.responses.*` directly. Prompt-cache key derivation stays in the existing policy helper and is passed to LangChain per invocation.

**Tech Stack:** Python 3.13.2, FastAPI, LangChain `langchain-openai` / `langchain-core`, OpenAI Responses API through `ChatOpenAI(use_responses_api=True)`, pytest, ruff, provider-neutral `src.observability`.

---

## Source Notes

- LangChain Python OpenAI docs require the `langchain-openai` package and show `ChatOpenAI` as the OpenAI chat integration.
- LangChain docs show `ChatOpenAI(..., use_responses_api=True)` for Responses API conversation state.
- LangChain docs show multimodal content blocks for images using either LangChain `"image"` blocks or OpenAI-compatible `"image_url"` blocks.
- LangChain docs show manual prompt caching by passing `prompt_cache_key` to `invoke` / `ainvoke`, and checking `response.usage_metadata.input_token_details.cache_read`.
- LangChain docs also show token usage in `response_metadata["token_usage"]["prompt_tokens_details"]["cached_tokens"]`, so usage extraction must support both LangChain-normalized and OpenAI-native metadata shapes.

References:
- `https://docs.langchain.com/oss/python/integrations/chat/openai`
- `https://reference.langchain.com/python/langchain-openai/chat_models/base/ChatOpenAI`

## Scope

In scope:
- Add `langchain-openai` as the OpenAI integration package.
- Replace direct `AsyncOpenAI.responses.parse/create` calls in `OpenAIProvider`.
- Preserve existing `OpenAIProvider.generate()` and `generate_with_vision()` contracts.
- Preserve `OPENAI_PROMPT_CACHE_*` settings and safe cache-key policy.
- Preserve prompt-cache metrics names and attributes.
- Preserve OpenAI error-code extraction.
- Preserve Cloudflare and Gemini-related code; do not remove other providers.

Out of scope:
- Replacing Cloudflare Workers AI.
- Replacing Gemini-related docs or fallback references.
- Adding LangGraph agents.
- Adding LangSmith runtime requirements.
- Changing public API schemas.
- Changing model fallback chains.

## File Map

- Modify: `pyproject.toml`
  - Responsibility: add `langchain-openai` dependency compatible with current `langchain-core`.
- Modify: `requirements.txt`
  - Responsibility: keep direct install path aligned with project dependencies.
- Modify: `uv.lock`
  - Responsibility: lock the new dependency after `uv add`.
- Create: `src/infra/services/ai/langchain_openai_adapter.py`
  - Responsibility: own all LangChain `ChatOpenAI` construction, message creation, structured-output invocation, raw invocation, vision invocation, output text extraction, and usage extraction.
- Create: `tests/unit/infra/services/ai/test_langchain_openai_adapter.py`
  - Responsibility: test LangChain adapter behavior without making network calls.
- Modify: `src/infra/services/ai/providers/openai_provider.py`
  - Responsibility: use `OpenAILangChainAdapter` instead of raw `AsyncOpenAI`; keep provider port behavior and metrics.
- Modify: `tests/unit/infra/services/ai/providers/test_openai_provider.py`
  - Responsibility: update provider tests to assert LangChain adapter calls instead of raw SDK calls.
- Modify: `README.md`
  - Responsibility: state OpenAI text/vision calls run through LangChain `ChatOpenAI`.
- Modify: `docs/external-services.md`
  - Responsibility: update OpenAI prompt-caching docs to mention LangChain invocation.

---

### Task 1: Add LangChain OpenAI Dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Modify: `uv.lock`

- [ ] **Step 1: Prove the package is currently absent**

Run:

```bash
.venv/bin/python - <<'PY'
import importlib.util

assert importlib.util.find_spec("langchain_core") is not None
assert importlib.util.find_spec("langchain_openai") is None
print("langchain_openai missing as expected")
PY
```

Expected:

```text
langchain_openai missing as expected
```

- [ ] **Step 2: Add the package with uv**

Run:

```bash
uv add "langchain-openai>=1.3.0,<2.0.0"
```

Expected:

```text
Resolved ...
Updated pyproject.toml
Updated uv.lock
```

If `requirements.txt` is not updated by the command, add this line under `# AI/LLM dependencies`:

```text
langchain-openai>=1.3.0,<2.0.0
```

- [ ] **Step 3: Verify imports and key LangChain symbols**

Run:

```bash
.venv/bin/python - <<'PY'
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

print(ChatOpenAI.__name__)
print(AIMessage.__name__, HumanMessage.__name__, SystemMessage.__name__)
PY
```

Expected:

```text
ChatOpenAI
AIMessage HumanMessage SystemMessage
```

- [ ] **Step 4: Commit dependency update**

Run:

```bash
git add pyproject.toml requirements.txt uv.lock
git commit -m "feat: add langchain openai dependency"
```

Expected:

```text
[codex/openai-provider-migration-pr1 ...] feat: add langchain openai dependency
```

---

### Task 2: Add LangChain OpenAI Adapter

**Files:**
- Create: `src/infra/services/ai/langchain_openai_adapter.py`
- Create: `tests/unit/infra/services/ai/test_langchain_openai_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/unit/infra/services/ai/test_langchain_openai_adapter.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
from src.infra.services.ai.langchain_openai_adapter import (
    LangChainOpenAIResult,
    OpenAILangChainAdapter,
)


def _adapter(monkeypatch):
    created = []

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.ainvoke = AsyncMock(
                return_value=AIMessage(
                    content="raw answer",
                    usage_metadata={
                        "input_tokens": 1500,
                        "input_token_details": {"cache_read": 512},
                    },
                    response_metadata={
                        "token_usage": {
                            "prompt_tokens": 1500,
                            "prompt_tokens_details": {"cached_tokens": 512},
                        }
                    },
                )
            )
            self.structured = MagicMock()
            self.structured.ainvoke = AsyncMock(
                return_value={
                    "raw": AIMessage(
                        content="",
                        usage_metadata={
                            "input_tokens": 1800,
                            "input_token_details": {"cache_read": 1024},
                        },
                    ),
                    "parsed": VisionNutritionResponse.model_validate(
                        {
                            "is_food": True,
                            "dish_name": "Chicken rice bowl",
                            "emoji": "🍚",
                            "foods": [
                                {
                                    "name": "grilled chicken",
                                    "quantity_g": 150.0,
                                    "macros": {
                                        "protein_g": 35.0,
                                        "carbs_g": 0.0,
                                        "fat_g": 5.0,
                                    },
                                    "confidence": 0.92,
                                }
                            ],
                            "confidence": 0.88,
                        }
                    ),
                    "parsing_error": None,
                }
            )
            created.append(self)

        def with_structured_output(self, schema, *, method, strict, include_raw):
            self.structured_schema = schema
            self.structured_kwargs = {
                "method": method,
                "strict": strict,
                "include_raw": include_raw,
            }
            return self.structured

    monkeypatch.setattr(
        "src.infra.services.ai.langchain_openai_adapter.ChatOpenAI",
        FakeChatOpenAI,
    )
    return (
        OpenAILangChainAdapter(
            api_key="test-key",
            request_timeout_seconds=20,
            max_retries=1,
            store_responses=False,
        ),
        created,
    )


@pytest.mark.asyncio
async def test_structured_text_uses_chat_openai_with_responses_api(monkeypatch):
    adapter, created = _adapter(monkeypatch)

    result = await adapter.generate_structured(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Chicken rice bowl",
        system_message="Return canonical JSON.",
        schema=VisionNutritionResponse,
        max_tokens=1500,
        request_kwargs={
            "prompt_cache_key": "mealtrack-test:parse_text:abc123",
            "prompt_cache_retention": "in_memory",
        },
    )

    assert isinstance(result, LangChainOpenAIResult)
    assert result.parsed.dish_name == "Chicken rice bowl"
    llm = created[0]
    assert llm.kwargs["model"] == "gpt-5.4-mini-2026-03-17"
    assert llm.kwargs["api_key"] == "test-key"
    assert llm.kwargs["timeout"] == 20
    assert llm.kwargs["max_retries"] == 1
    assert llm.kwargs["use_responses_api"] is True
    assert llm.kwargs["reasoning"] == {"effort": "none"}
    assert llm.kwargs["max_tokens"] == 1500
    assert llm.structured_schema is VisionNutritionResponse
    assert llm.structured_kwargs == {
        "method": "json_schema",
        "strict": True,
        "include_raw": True,
    }
    messages = llm.structured.ainvoke.await_args.args[0]
    assert messages == [
        SystemMessage(content="Return canonical JSON."),
        HumanMessage(content="Chicken rice bowl"),
    ]
    assert llm.structured.ainvoke.await_args.kwargs["prompt_cache_key"].startswith(
        "mealtrack-test:parse_text:"
    )
    assert llm.structured.ainvoke.await_args.kwargs["prompt_cache_retention"] == (
        "in_memory"
    )
    assert llm.structured.ainvoke.await_args.kwargs["store"] is False


@pytest.mark.asyncio
async def test_raw_text_returns_text_and_usage(monkeypatch):
    adapter, created = _adapter(monkeypatch)

    result = await adapter.generate_raw(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Summarize.",
        system_message="Be concise.",
        max_tokens=None,
        request_kwargs={"prompt_cache_key": "mealtrack-test:general:abc123"},
    )

    assert result.parsed == {"raw_content": "raw answer"}
    assert adapter.input_tokens(result.raw_message) == 1500
    assert adapter.cached_tokens(result.raw_message) == 512
    messages = created[0].ainvoke.await_args.args[0]
    assert messages == [
        SystemMessage(content="Be concise."),
        HumanMessage(content="Summarize."),
    ]


@pytest.mark.asyncio
async def test_vision_uses_langchain_multimodal_content(monkeypatch):
    adapter, created = _adapter(monkeypatch)

    result = await adapter.generate_vision_structured(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Identify food.",
        image_data=b"image-bytes",
        image_mime_type="image/png",
        system_message="Return canonical JSON.",
        schema=VisionNutritionResponse,
        max_tokens=1500,
        request_kwargs={"prompt_cache_key": "mealtrack-test:meal_scan:abc123"},
    )

    assert result.parsed.dish_name == "Chicken rice bowl"
    messages = created[0].structured.ainvoke.await_args.args[0]
    assert messages[0] == SystemMessage(content="Return canonical JSON.")
    assert messages[1].content[0] == {"type": "text", "text": "Identify food."}
    assert messages[1].content[1]["type"] == "image_url"
    assert messages[1].content[1]["image_url"]["url"].startswith(
        "data:image/png;base64,"
    )


def test_usage_extractors_support_response_metadata_fallback():
    message = SimpleNamespace(
        usage_metadata={},
        response_metadata={
            "token_usage": {
                "prompt_tokens": 1400,
                "prompt_tokens_details": {"cached_tokens": 700},
            }
        },
    )
    adapter = OpenAILangChainAdapter(
        api_key="test-key",
        request_timeout_seconds=20,
        max_retries=1,
        store_responses=False,
    )

    assert adapter.input_tokens(message) == 1400
    assert adapter.cached_tokens(message) == 700
```

- [ ] **Step 2: Run adapter tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/test_langchain_openai_adapter.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'src.infra.services.ai.langchain_openai_adapter'
```

- [ ] **Step 3: Implement the adapter**

Create `src/infra/services/ai/langchain_openai_adapter.py`:

```python
"""LangChain-backed OpenAI invocation adapter."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


@dataclass(frozen=True)
class LangChainOpenAIResult:
    parsed: Any
    raw_message: Any


class OpenAILangChainAdapter:
    """Owns LangChain ChatOpenAI construction and invocation details."""

    def __init__(
        self,
        *,
        api_key: str,
        request_timeout_seconds: int,
        max_retries: int,
        store_responses: bool,
    ) -> None:
        self._api_key = api_key
        self._request_timeout_seconds = request_timeout_seconds
        self._max_retries = max_retries
        self._store_responses = store_responses

    def _llm(self, *, model: str, max_tokens: int | None) -> ChatOpenAI:
        kwargs: dict[str, Any] = {
            "model": model,
            "api_key": self._api_key,
            "timeout": self._request_timeout_seconds,
            "max_retries": self._max_retries,
            "use_responses_api": True,
            "reasoning": {"effort": "none"},
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        return ChatOpenAI(**kwargs)

    async def generate_structured(
        self,
        *,
        model: str,
        prompt: str,
        system_message: str,
        schema: type,
        max_tokens: int | None,
        request_kwargs: dict[str, Any],
    ) -> LangChainOpenAIResult:
        llm = self._llm(model=model, max_tokens=max_tokens)
        structured_llm = llm.with_structured_output(
            schema,
            method="json_schema",
            strict=True,
            include_raw=True,
        )
        response = await structured_llm.ainvoke(
            self._text_messages(system_message=system_message, prompt=prompt),
            **self._request_kwargs(request_kwargs),
        )
        parsing_error = response.get("parsing_error")
        if parsing_error is not None:
            raise parsing_error
        return LangChainOpenAIResult(
            parsed=response["parsed"],
            raw_message=response["raw"],
        )

    async def generate_raw(
        self,
        *,
        model: str,
        prompt: str,
        system_message: str,
        max_tokens: int | None,
        request_kwargs: dict[str, Any],
    ) -> LangChainOpenAIResult:
        llm = self._llm(model=model, max_tokens=max_tokens)
        response = await llm.ainvoke(
            self._text_messages(system_message=system_message, prompt=prompt),
            **self._request_kwargs(request_kwargs),
        )
        return LangChainOpenAIResult(
            parsed={"raw_content": self.text(response)},
            raw_message=response,
        )

    async def generate_vision_structured(
        self,
        *,
        model: str,
        prompt: str,
        image_data: bytes,
        image_mime_type: str,
        system_message: str | None,
        schema: type,
        max_tokens: int | None,
        request_kwargs: dict[str, Any],
    ) -> LangChainOpenAIResult:
        llm = self._llm(model=model, max_tokens=max_tokens)
        structured_llm = llm.with_structured_output(
            schema,
            method="json_schema",
            strict=True,
            include_raw=True,
        )
        image_b64 = base64.b64encode(image_data).decode("ascii")
        data_url = f"data:{image_mime_type};base64,{image_b64}"
        messages: list[BaseMessage] = [
            SystemMessage(content=system_message or ""),
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            ),
        ]
        response = await structured_llm.ainvoke(
            messages,
            **self._request_kwargs(request_kwargs),
        )
        parsing_error = response.get("parsing_error")
        if parsing_error is not None:
            raise parsing_error
        return LangChainOpenAIResult(
            parsed=response["parsed"],
            raw_message=response["raw"],
        )

    def _request_kwargs(self, request_kwargs: dict[str, Any]) -> dict[str, Any]:
        kwargs = dict(request_kwargs)
        kwargs["store"] = self._store_responses
        return kwargs

    @staticmethod
    def _text_messages(*, system_message: str, prompt: str) -> list[BaseMessage]:
        return [
            SystemMessage(content=system_message),
            HumanMessage(content=prompt),
        ]

    @staticmethod
    def text(message: AIMessage) -> str:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for block in content:
                if isinstance(block, str):
                    chunks.append(block)
                elif isinstance(block, dict) and isinstance(block.get("text"), str):
                    chunks.append(block["text"])
            return "".join(chunks)
        return str(content)

    @staticmethod
    def input_tokens(message: Any) -> float:
        usage = _mapping(getattr(message, "usage_metadata", None))
        if usage.get("input_tokens") is not None:
            return float(usage["input_tokens"])
        token_usage = _mapping(
            _mapping(getattr(message, "response_metadata", None)).get("token_usage")
        )
        return float(token_usage.get("prompt_tokens") or 0)

    @staticmethod
    def cached_tokens(message: Any) -> float:
        usage = _mapping(getattr(message, "usage_metadata", None))
        input_details = _mapping(usage.get("input_token_details"))
        if input_details.get("cache_read") is not None:
            return float(input_details["cache_read"])
        token_usage = _mapping(
            _mapping(getattr(message, "response_metadata", None)).get("token_usage")
        )
        prompt_details = _mapping(token_usage.get("prompt_tokens_details"))
        return float(prompt_details.get("cached_tokens") or 0)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}
```

- [ ] **Step 4: Run adapter tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/test_langchain_openai_adapter.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Lint adapter files**

Run:

```bash
.venv/bin/python -m ruff check src/infra/services/ai/langchain_openai_adapter.py tests/unit/infra/services/ai/test_langchain_openai_adapter.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 6: Commit adapter**

Run:

```bash
git add src/infra/services/ai/langchain_openai_adapter.py \
  tests/unit/infra/services/ai/test_langchain_openai_adapter.py
git commit -m "feat: add langchain openai adapter"
```

Expected:

```text
[codex/openai-provider-migration-pr1 ...] feat: add langchain openai adapter
```

---

### Task 3: Refactor OpenAIProvider To Use LangChain

**Files:**
- Modify: `src/infra/services/ai/providers/openai_provider.py`
- Modify: `tests/unit/infra/services/ai/providers/test_openai_provider.py`

- [ ] **Step 1: Replace provider tests with adapter-based expectations**

In `tests/unit/infra/services/ai/providers/test_openai_provider.py`, replace raw SDK mock expectations with this complete file:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
from src.domain.ports.ai_provider_port import AICapability
from src.infra.services.ai.langchain_openai_adapter import LangChainOpenAIResult
from src.infra.services.ai.providers.openai_provider import OpenAIProvider


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


def _parsed_vision_response():
    return VisionNutritionResponse.model_validate(
        {
            "is_food": True,
            "dish_name": "Chicken rice bowl",
            "emoji": "🍚",
            "foods": [
                {
                    "name": "grilled chicken",
                    "quantity_g": 150.0,
                    "macros": {
                        "protein_g": 35.0,
                        "carbs_g": 0.0,
                        "fat_g": 5.0,
                    },
                    "confidence": 0.92,
                }
            ],
            "confidence": 0.88,
        }
    )


def _raw_message(input_tokens=1500, cached_tokens=1024):
    return SimpleNamespace(
        usage_metadata={
            "input_tokens": input_tokens,
            "input_token_details": {"cache_read": cached_tokens},
        },
        response_metadata={},
    )


def test_openai_provider_capabilities():
    provider = _provider()

    assert provider.provider_name == "openai"
    assert AICapability.TEXT_GENERATION in provider.supported_capabilities
    assert AICapability.VISION in provider.supported_capabilities
    assert AICapability.STRUCTURED_OUTPUT in provider.supported_capabilities


@pytest.mark.asyncio
async def test_generate_structured_text_uses_langchain_adapter():
    provider = _provider()
    parsed = _parsed_vision_response()
    provider._langchain.generate_structured = AsyncMock(
        return_value=LangChainOpenAIResult(parsed=parsed, raw_message=_raw_message())
    )

    result = await provider.generate(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Chicken rice bowl",
        system_message="Return canonical JSON.",
        schema=VisionNutritionResponse,
        purpose_hint="parse_text",
        max_tokens=1500,
    )

    assert result["emoji"] == "🍚"
    kwargs = provider._langchain.generate_structured.await_args.kwargs
    assert kwargs["model"] == "gpt-5.4-mini-2026-03-17"
    assert kwargs["prompt"] == "Chicken rice bowl"
    assert kwargs["system_message"] == "Return canonical JSON."
    assert kwargs["schema"] is VisionNutritionResponse
    assert kwargs["max_tokens"] == 1500
    assert kwargs["request_kwargs"]["prompt_cache_key"].startswith(
        "mealtrack-test:parse_text:"
    )
    assert kwargs["request_kwargs"]["prompt_cache_retention"] == "in_memory"


@pytest.mark.asyncio
async def test_generate_raw_text_uses_langchain_adapter():
    provider = _provider()
    provider._langchain.generate_raw = AsyncMock(
        return_value=LangChainOpenAIResult(
            parsed={"raw_content": "ok"},
            raw_message=_raw_message(input_tokens=1300, cached_tokens=0),
        )
    )

    result = await provider.generate(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Generate summary.",
        system_message="Be concise.",
        purpose_hint="general",
    )

    assert result == {"raw_content": "ok"}
    kwargs = provider._langchain.generate_raw.await_args.kwargs
    assert kwargs["request_kwargs"]["prompt_cache_key"].startswith(
        "mealtrack-test:general:"
    )


@pytest.mark.asyncio
async def test_generate_with_vision_uses_langchain_adapter():
    provider = _provider()
    parsed = _parsed_vision_response()
    provider._langchain.generate_vision_structured = AsyncMock(
        return_value=LangChainOpenAIResult(parsed=parsed, raw_message=_raw_message())
    )

    result = await provider.generate_with_vision(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Identify food.",
        image_data=b"image-bytes",
        system_message="Return canonical JSON.",
        schema=VisionNutritionResponse,
        image_mime_type="image/png",
        max_tokens=1500,
        purpose_hint="meal_scan",
    )

    assert result["emoji"] == "🍚"
    kwargs = provider._langchain.generate_vision_structured.await_args.kwargs
    assert kwargs["image_data"] == b"image-bytes"
    assert kwargs["image_mime_type"] == "image/png"
    assert kwargs["request_kwargs"]["prompt_cache_key"].startswith(
        "mealtrack-test:meal_scan:"
    )


@pytest.mark.asyncio
async def test_records_prompt_cache_usage_metrics(monkeypatch):
    provider = _provider()
    parsed = _parsed_vision_response()
    provider._langchain.generate_structured = AsyncMock(
        return_value=LangChainOpenAIResult(
            parsed=parsed,
            raw_message=_raw_message(input_tokens=1500, cached_tokens=1024),
        )
    )
    provider._langchain.input_tokens = MagicMock(return_value=1500)
    provider._langchain.cached_tokens = MagicMock(return_value=1024)
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

- [ ] **Step 2: Run provider tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/providers/test_openai_provider.py -q
```

Expected:

```text
AttributeError: 'OpenAIProvider' object has no attribute '_langchain'
```

- [ ] **Step 3: Refactor provider imports and constructor**

In `src/infra/services/ai/providers/openai_provider.py`, remove `base64` and `AsyncOpenAI` imports. Keep OpenAI exception imports for `extract_error_code`. Add:

```python
from src.infra.services.ai.langchain_openai_adapter import OpenAILangChainAdapter
```

Replace the constructor body with:

```python
        self._langchain = OpenAILangChainAdapter(
            api_key=api_key,
            request_timeout_seconds=request_timeout_seconds,
            max_retries=max_retries,
            store_responses=store_responses,
        )
        self._prompt_cache_policy = OpenAIPromptCachePolicy(
            enabled=prompt_cache_enabled,
            key_prefix=prompt_cache_key_prefix,
            retention=prompt_cache_retention,
        )
```

- [ ] **Step 4: Replace usage recording**

Replace `_record_prompt_cache_usage(...)` with:

```python
    def _record_prompt_cache_usage(
        self,
        raw_message: Any,
        *,
        model: str,
        purpose_hint: str | None,
    ) -> None:
        input_tokens = self._langchain.input_tokens(raw_message)
        cached_tokens = self._langchain.cached_tokens(raw_message)
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

Delete the module-level `_usage_number(...)` helper because LangChain usage extraction now lives in `OpenAILangChainAdapter`.

- [ ] **Step 5: Refactor `generate()`**

Replace the schema branch in `generate()` with:

```python
        if schema is not None:
            result = await self._langchain.generate_structured(
                model=model,
                prompt=prompt,
                system_message=system_message,
                schema=schema,
                max_tokens=max_tokens,
                request_kwargs=prompt_cache_kwargs,
            )
            self._record_prompt_cache_usage(
                result.raw_message,
                model=model,
                purpose_hint=purpose_hint,
            )
            return self._dump_parsed(result.parsed)
```

Replace the non-schema branch in `generate()` with:

```python
        result = await self._langchain.generate_raw(
            model=model,
            prompt=prompt,
            system_message=system_message,
            max_tokens=max_tokens,
            request_kwargs=prompt_cache_kwargs,
        )
        self._record_prompt_cache_usage(
            result.raw_message,
            model=model,
            purpose_hint=purpose_hint,
        )
        return self._dump_parsed(result.parsed)
```

- [ ] **Step 6: Refactor `generate_with_vision()`**

Replace the body after `prompt_cache_kwargs = ...` with:

```python
        result = await self._langchain.generate_vision_structured(
            model=model,
            prompt=prompt,
            image_data=image_data,
            image_mime_type=image_mime_type,
            system_message=system_message,
            schema=schema,
            max_tokens=max_tokens,
            request_kwargs=prompt_cache_kwargs,
        )
        self._record_prompt_cache_usage(
            result.raw_message,
            model=model,
            purpose_hint=purpose_hint,
        )
        return self._dump_parsed(result.parsed)
```

- [ ] **Step 7: Run provider tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/infra/services/ai/providers/test_openai_provider.py -q
```

Expected:

```text
6 passed
```

- [ ] **Step 8: Run adapter and provider tests together**

Run:

```bash
.venv/bin/python -m pytest \
  tests/unit/infra/services/ai/test_langchain_openai_adapter.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py \
  -q
```

Expected:

```text
10 passed
```

- [ ] **Step 9: Lint touched files**

Run:

```bash
.venv/bin/python -m ruff check \
  src/infra/services/ai/langchain_openai_adapter.py \
  src/infra/services/ai/providers/openai_provider.py \
  tests/unit/infra/services/ai/test_langchain_openai_adapter.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 10: Commit provider refactor**

Run:

```bash
git add src/infra/services/ai/providers/openai_provider.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py
git commit -m "refactor: use langchain openai provider path"
```

Expected:

```text
[codex/openai-provider-migration-pr1 ...] refactor: use langchain openai provider path
```

---

### Task 4: Update Docs For LangChain Contract

**Files:**
- Modify: `README.md`
- Modify: `docs/external-services.md`
- Modify: `docs/superpowers/plans/2026-06-26-openai-prompt-caching.md`

- [ ] **Step 1: Update README AI stack line**

In `README.md`, change the AI stack bullet to:

```markdown
- **AI**: LangChain `ChatOpenAI` over OpenAI Responses API for text/vision, Cloudflare Workers AI embeddings/fallback, Pinecone Inference API (1024-dim).
```

- [ ] **Step 2: Update README prompt caching section**

Replace the OpenAI prompt caching bullets with:

```markdown
### OpenAI Prompt Caching

- OpenAI calls run through LangChain `ChatOpenAI` with Responses API enabled.
- Enable provider-side prompt caching with `OPENAI_PROMPT_CACHE_ENABLED`.
- Optional retention uses `OPENAI_PROMPT_CACHE_RETENTION`; key namespace uses `OPENAI_PROMPT_CACHE_KEY_PREFIX`.
- Cache keys are derived from the model, purpose, and a hash of the system prompt. They never include raw user prompt text, images, emails, or IDs.
- Track `ai.openai.prompt_cache.request.count`, `ai.openai.prompt_cache.cached_tokens`, and `ai.openai.prompt_cache.input_tokens` before assuming savings.
```

- [ ] **Step 3: Update external services prompt caching section**

In `docs/external-services.md`, replace the OpenAI Responses API Prompt Caching section with:

```markdown
## OpenAI Responses API Prompt Caching

**Purpose:** Best-effort provider-side prefix caching for repeated long OpenAI requests through LangChain `ChatOpenAI`.

- OpenAI text and vision calls use LangChain `ChatOpenAI` with Responses API enabled.
- Enabled with `OPENAI_PROMPT_CACHE_ENABLED`.
- Optional retention uses `OPENAI_PROMPT_CACHE_RETENTION`; key namespace uses `OPENAI_PROMPT_CACHE_KEY_PREFIX`.
- Cache keys are derived from the model, purpose, and a hash of the system prompt. They never contain raw user prompt text, images, emails, or IDs.
- Prompt caching only helps when the repeated prefix is at least 1024 tokens. Shorter prompts should not be expected to benefit.
- Treat caching as best-effort, not guaranteed savings. Monitor `ai.openai.prompt_cache.request.count`, `ai.openai.prompt_cache.cached_tokens`, and `ai.openai.prompt_cache.input_tokens` before claiming cost reduction.
- Cached-token evidence comes from LangChain `AIMessage.usage_metadata.input_token_details.cache_read` or OpenAI-native token metadata when LangChain exposes it in `response_metadata`.
```

- [ ] **Step 4: Update the existing prompt-caching plan note**

In `docs/superpowers/plans/2026-06-26-openai-prompt-caching.md`, add this note immediately below the `**Tech Stack:**` line:

```markdown
> Follow-up note: the OpenAI call path is being migrated from raw `openai.AsyncOpenAI` calls to LangChain `ChatOpenAI` in `docs/superpowers/plans/2026-06-26-langchain-openai-provider.md`. The prompt-cache policy, settings, and metric names remain valid.
```

- [ ] **Step 5: Verify docs mention LangChain**

Run:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path

readme = Path("README.md").read_text()
external = Path("docs/external-services.md").read_text()
plan = Path("docs/superpowers/plans/2026-06-26-openai-prompt-caching.md").read_text()

assert "LangChain `ChatOpenAI`" in readme
assert "LangChain `ChatOpenAI`" in external
assert "langchain-openai-provider" in plan
print("LangChain docs updated")
PY
```

Expected:

```text
LangChain docs updated
```

- [ ] **Step 6: Commit docs update**

Run:

```bash
git add README.md docs/external-services.md \
  docs/superpowers/plans/2026-06-26-openai-prompt-caching.md
git commit -m "feat: document langchain openai provider path"
```

Expected:

```text
[codex/openai-provider-migration-pr1 ...] feat: document langchain openai provider path
```

---

### Task 5: Regression Sweep

**Files:**
- No required edits unless a test exposes a real regression.

- [ ] **Step 1: Run focused LangChain/OpenAI tests**

Run:

```bash
.venv/bin/python -m pytest \
  tests/unit/infra/services/ai/test_langchain_openai_adapter.py \
  tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py \
  tests/unit/infra/services/ai/test_ai_vision_failure_routing.py \
  tests/unit/infra/monitoring/test_observability_facade.py \
  -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 2: Run original collection-sensitive set**

Run:

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
  tests/unit/infra/monitoring/test_observability_facade.py \
  -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 3: Run lint over touched Python files**

Run:

```bash
.venv/bin/python -m ruff check \
  src/infra/services/ai/langchain_openai_adapter.py \
  src/infra/services/ai/openai_prompt_cache_policy.py \
  src/infra/services/ai/providers/openai_provider.py \
  src/infra/services/ai/ai_model_manager.py \
  src/infra/config/settings.py \
  src/observability_connectors.py \
  tests/unit/infra/services/ai/test_langchain_openai_adapter.py \
  tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py \
  tests/unit/infra/services/ai/test_ai_vision_failure_routing.py \
  tests/unit/infra/monitoring/test_observability_facade.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 4: Run full unit suite**

Run:

```bash
.venv/bin/python -m pytest tests/unit -q
```

Expected:

```text
1740+ passed, skips acceptable if they match existing skip reasons
```

- [ ] **Step 5: Push and let the pre-push hook rerun tests**

Run:

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
| LangChain migration breaks provider port behavior | High | `OpenAIProvider` public methods and return shapes remain unchanged; tests assert raw, structured, and vision paths. |
| Structured output loses token usage | High | Adapter uses `with_structured_output(..., include_raw=True)` and returns both parsed output and raw `AIMessage`. |
| Prompt cache metrics lose cached tokens | High | Adapter extracts both LangChain `usage_metadata.input_token_details.cache_read` and OpenAI-native `response_metadata.token_usage.prompt_tokens_details.cached_tokens`. |
| Prompt cache kwargs are not passed through LangChain | High | Tests assert `prompt_cache_key` and `prompt_cache_retention` are passed to `.ainvoke(...)`. |
| Vision payload format drifts from LangChain conventions | Medium | Adapter tests assert multimodal `HumanMessage` content uses an OpenAI-compatible `image_url` data URL block. |
| `store_responses` silently disappears | Medium | Adapter adds `store` to every invocation kwargs dictionary and tests assert it. |
| File growth worsens provider maintainability | Medium | LangChain-specific message construction and usage extraction move into `langchain_openai_adapter.py`; provider stays focused on port-level orchestration. |
| Existing staged local plan file is accidentally committed | Medium | Execution should use explicit `git add` pathspecs and avoid staging `docs/superpowers/plans/2026-06-25-openai-provider-migration.md` unless the user explicitly asks. |

## Self-Review

Spec coverage:
- "Use langchain open ai instead of pure open ai": Tasks 1-3 add `langchain-openai` and remove direct `AsyncOpenAI.responses.*` calls from the provider path.
- "Follow langchain framework": Adapter uses `ChatOpenAI`, LangChain message objects, `with_structured_output`, async `ainvoke`, and LangChain usage metadata.
- Preserve PR-1 prompt caching: Tasks 2-3 keep existing prompt-cache policy and pass kwargs through LangChain.
- Preserve metrics: Task 3 records the same metric names from LangChain raw messages.
- Docs: Task 4 updates README, external services, and links this follow-up to the prompt-caching plan.

Placeholder scan:
- No deferred implementation markers.
- No undefined helper names after Task 2.
- No cross-task shorthand shortcuts.

Type consistency:
- `OpenAILangChainAdapter.generate_structured(...)`, `generate_raw(...)`, and `generate_vision_structured(...)` all return `LangChainOpenAIResult`.
- `OpenAIProvider._record_prompt_cache_usage(...)` consumes the `raw_message` returned by the adapter.
- Prompt-cache kwargs remain a `dict[str, Any]` from `OpenAIPromptCachePolicy.request_kwargs(...)`.

## Execution Handoff

Plan complete. Use one of:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.
