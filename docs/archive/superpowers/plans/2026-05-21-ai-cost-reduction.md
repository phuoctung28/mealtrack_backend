# AI Cost Reduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce Gemini AI spend by ≥70% by fixing 6 silent bugs, removing unused providers, consolidating prompt rules, and adding observability.

**Architecture:** Three independent phases — quick wins (token/routing fixes), prompt architecture (system message split + rule consolidation), and observability (PostHog LLM Analytics + explicit caching). Each phase ships as its own PR and is safe to deploy independently.

**Tech Stack:** Python 3.11, FastAPI, LangChain, Google Gemini 2.5 Flash / Flash-Lite, Redis, `posthog[otel]`, `opentelemetry-instrumentation-langchain`

---

## File Map

### Phase 1 — Quick Wins
| File | Change |
|---|---|
| `src/infra/services/ai/gemini_model_config.py` | Collapse RECIPE_PRIMARY/SECONDARY → RECIPE, add PURPOSE_TEMPERATURES |
| `src/infra/services/ai/gemini_model_manager.py` | Purpose-based temperature, fix thinking budget check |
| `src/infra/services/ai/ai_model_manager.py` | ModelPurpose collapse, Mistral removal, purpose_hint forwarding |
| `src/infra/services/ai/providers/gemini_provider.py` | Accept purpose_hint, fix MODEL_PURPOSE_MAP routing |
| `src/infra/adapters/meal_generation_service.py` | Update PURPOSE_MAP string keys |
| `src/domain/services/meal_suggestion/recipe_attempt_builder.py` | Token limit 4000 → 1200 |
| `src/infra/adapters/vision_ai_service.py` | Pass max_tokens=1024 in both generate_with_vision calls |
| **Delete** `src/infra/services/ai/providers/mistral_provider.py` | Removed entirely |
| **Delete** `src/infra/services/ai/providers/kimi_provider.py` | Unused |

### Phase 2 — Prompt Architecture
| File | Change |
|---|---|
| `src/domain/services/prompts/prompt_constants.py` | Single source of truth for all rules |
| `src/infra/services/ai/prompts/system_prompts.py` | Add RECIPE_GENERATION, VISION_ANALYSIS constants (≥1024 tokens each) |
| `src/domain/strategies/meal_analysis_strategy.py` | Modernise 4 verbose strategies; remove duplicate rule constants |
| `src/domain/services/meal_suggestion/parallel_recipe_generator.py` | Use SystemPrompts.RECIPE_GENERATION, remove 3 inline copies |

### Phase 3 — Observability + Caching
| File | Change |
|---|---|
| `requirements.txt` | Add posthog[otel], opentelemetry-instrumentation-langchain |
| `src/api/main.py` | Init OpenTelemetry + LangchainInstrumentor in lifespan |
| **New** `src/infra/services/ai/gemini_cache_manager.py` | Explicit cache lifecycle |
| `src/infra/services/ai/providers/gemini_provider.py` | Accept cached_content, skip system message when cache active |
| `src/infra/services/ai/gemini_model_manager.py` | Forward cached_content to ChatGoogleGenerativeAI |

---

## Phase 1 — Quick Wins

### Task 1: Collapse RECIPE_PRIMARY/SECONDARY → RECIPE

**Why:** `RECIPE_PRIMARY` and `RECIPE_SECONDARY` both default to the same model (`gemini-2.5-flash`). The alternation logic in `parallel_recipe_generator.py` provides no actual load distribution. Collapse to one `RECIPE` purpose; use Flash-Lite as primary (cheaper, less 503 pressure).

**Files:**
- Modify: `src/infra/services/ai/gemini_model_config.py`
- Modify: `src/infra/services/ai/gemini_model_manager.py`
- Modify: `src/infra/services/ai/ai_model_manager.py`
- Modify: `src/infra/adapters/meal_generation_service.py`
- Modify: `src/domain/services/meal_suggestion/parallel_recipe_generator.py` (lines ~500–530)
- Test: `tests/unit/infra/services/ai/test_ai_model_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/services/ai/test_ai_model_manager.py
# Add inside class TestModelSelection:

def test_recipe_purpose_exists(self, manager):
    """RECIPE is a valid purpose; RECIPE_PRIMARY and RECIPE_SECONDARY do not exist."""
    from src.infra.services.ai.ai_model_manager import ModelPurpose
    assert hasattr(ModelPurpose, "RECIPE")
    assert not hasattr(ModelPurpose, "RECIPE_PRIMARY")
    assert not hasattr(ModelPurpose, "RECIPE_SECONDARY")

def test_recipe_chain_uses_flash_lite_first(self, manager):
    """Flash-Lite is primary for recipes (cheaper, less 503 pressure)."""
    chain = manager.get_fallback_chain(ModelPurpose.RECIPE)
    assert chain[0] == "gemini-2.5-flash-lite"
    assert chain[1] == "gemini-2.5-flash"
    assert "mistral" not in " ".join(chain)
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/unit/infra/services/ai/test_ai_model_manager.py::TestModelSelection::test_recipe_purpose_exists -v
```
Expected: `FAILED` — `ModelPurpose` has no `RECIPE` attribute yet.

- [ ] **Step 3: Update gemini_model_config.py**

Replace the `GeminiModelPurpose` enum, `PURPOSE_MODEL_DEFAULTS`, and `PURPOSE_ENV_VARS`:

```python
# src/infra/services/ai/gemini_model_config.py

class GeminiModelPurpose(str, Enum):
    GENERAL = "general"
    MEAL_NAMES = "meal_names"
    RECIPE = "recipe"          # collapsed from RECIPE_PRIMARY + RECIPE_SECONDARY
    BARCODE = "barcode"


PURPOSE_MODEL_DEFAULTS = {
    GeminiModelPurpose.GENERAL:    "gemini-2.5-flash",
    GeminiModelPurpose.MEAL_NAMES: "gemini-2.5-flash-lite",
    GeminiModelPurpose.RECIPE:     "gemini-2.5-flash-lite",  # Flash-Lite primary
    GeminiModelPurpose.BARCODE:    "gemini-2.5-flash-lite",
}

PURPOSE_ENV_VARS = {
    GeminiModelPurpose.GENERAL:    "GEMINI_MODEL",
    GeminiModelPurpose.MEAL_NAMES: "GEMINI_MODEL_NAMES",
    GeminiModelPurpose.RECIPE:     "GEMINI_MODEL_RECIPE",
    GeminiModelPurpose.BARCODE:    "GEMINI_MODEL",
}
```

- [ ] **Step 4: Update gemini_model_manager.py thinking budget check**

Find the `if purpose in (...)` block at line ~198 and replace:

```python
# Before
if purpose in (
    GeminiModelPurpose.RECIPE_PRIMARY,
    GeminiModelPurpose.RECIPE_SECONDARY,
    GeminiModelPurpose.BARCODE,
):

# After
if purpose in (GeminiModelPurpose.RECIPE, GeminiModelPurpose.BARCODE):
```

- [ ] **Step 5: Update ai_model_manager.py ModelPurpose enum and FALLBACK_CHAINS**

```python
# src/infra/services/ai/ai_model_manager.py

class ModelPurpose(Enum):
    MEAL_SCAN        = "meal_scan"
    INGREDIENT_SCAN  = "ingredient_scan"
    PARSE_TEXT       = "parse_text"
    BARCODE          = "barcode"
    MEAL_NAMES       = "meal_names"
    RECIPE           = "recipe"          # collapsed
    DISCOVERY        = "discovery"
    GENERAL          = "general"


FALLBACK_CHAINS: Dict[ModelPurpose, List[str]] = {
    ModelPurpose.MEAL_SCAN:       ["gemini-2.5-flash", "gemini-2.5-flash-lite"],
    ModelPurpose.INGREDIENT_SCAN: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.PARSE_TEXT:      ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.BARCODE:         ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.MEAL_NAMES:      ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.DISCOVERY:       ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.GENERAL:         ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.RECIPE:          ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
}
```

- [ ] **Step 6: Update meal_generation_service.py PURPOSE_MAP**

```python
# src/infra/adapters/meal_generation_service.py

PURPOSE_MAP = {
    "meal_names": ModelPurpose.MEAL_NAMES,
    "recipe":     ModelPurpose.RECIPE,       # was recipe_primary / recipe_secondary
    "barcode":    ModelPurpose.BARCODE,
    "general":    ModelPurpose.GENERAL,
}
```

- [ ] **Step 7: Update parallel_recipe_generator.py — remove alternation logic**

Find the `_generate_with_retry` method (lines ~490–535) where `primary = "recipe_primary" if index % 2 == 0 else "recipe_secondary"`. Replace both string values with `"recipe"`:

```python
async def _generate_with_retry(
    self,
    prompt: str,
    meal_name: str,
    index: int,
    recipe_system: str,
    session: SuggestionSession,
    reject_on_scale_out_of_range: bool = True,
    fill_missing_steps: bool = False,
) -> Optional[MealSuggestion]:
    """Try recipe model; retry on same pool if first attempt fails."""
    result = await attempt_recipe_generation(
        self._generation,
        self._macro_validator,
        self._nutrition_lookup,
        prompt,
        meal_name,
        index,
        "recipe",        # was: "recipe_primary" if index % 2 == 0 else "recipe_secondary"
        recipe_system,
        session,
        reject_on_scale_out_of_range=reject_on_scale_out_of_range,
        fill_missing_steps=fill_missing_steps,
        recipe_schema=self._recipe_details_schema,
    )
    if result is not None:
        return result
    logger.debug(f"[PHASE-2-RETRY] index={index} | meal={meal_name}")
    return await attempt_recipe_generation(
        self._generation,
        self._macro_validator,
        self._nutrition_lookup,
        prompt,
        meal_name,
        index,
        "recipe",        # was: alternate pool string
        recipe_system,
        session,
        is_retry=True,
        reject_on_scale_out_of_range=reject_on_scale_out_of_range,
        fill_missing_steps=fill_missing_steps,
        recipe_schema=self._recipe_details_schema,
    )
```

- [ ] **Step 8: Run tests**

```
pytest tests/unit/infra/services/ai/test_ai_model_manager.py -v
```
Expected: all tests pass. Fix any that reference `RECIPE_PRIMARY`/`RECIPE_SECONDARY`.

- [ ] **Step 9: Commit**

```bash
git add src/infra/services/ai/gemini_model_config.py \
        src/infra/services/ai/gemini_model_manager.py \
        src/infra/services/ai/ai_model_manager.py \
        src/infra/adapters/meal_generation_service.py \
        src/domain/services/meal_suggestion/parallel_recipe_generator.py \
        tests/unit/infra/services/ai/test_ai_model_manager.py
git commit -m "refactor: collapse RECIPE_PRIMARY/SECONDARY into single RECIPE purpose

Flash-Lite is now the primary for recipes (cheaper, less 503 pressure).
Both original purposes used the same model — no load distribution was happening.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Add PURPOSE_TEMPERATURES + fix temperature default

**Why:** `get_model_for_purpose()` hardcodes `temperature=0.7` for all purposes. Structured JSON extraction (barcode, text parsing) should use 0.1 to reduce hallucination and parse failures. Recipe generation uses 0.4. Meal names keep 0.7 for diversity.

**Files:**
- Modify: `src/infra/services/ai/gemini_model_config.py`
- Modify: `src/infra/services/ai/gemini_model_manager.py`
- Test: `tests/unit/infra/services/ai/test_ai_model_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/services/ai/providers/test_gemini_provider.py  (create if not exists)
import pytest
from unittest.mock import patch, MagicMock
from src.infra.services.ai.gemini_model_config import (
    GeminiModelPurpose,
    PURPOSE_TEMPERATURES,
)


def test_purpose_temperatures_defined():
    assert PURPOSE_TEMPERATURES[GeminiModelPurpose.BARCODE] == 0.1
    assert PURPOSE_TEMPERATURES[GeminiModelPurpose.MEAL_NAMES] == 0.7
    assert PURPOSE_TEMPERATURES[GeminiModelPurpose.RECIPE] == 0.4
    assert PURPOSE_TEMPERATURES[GeminiModelPurpose.GENERAL] == 0.2


def test_get_model_for_purpose_uses_purpose_temperature():
    """When temperature is not passed, purpose-specific temperature is used."""
    from src.infra.services.ai.gemini_model_manager import GeminiModelManager

    mock_model = MagicMock()
    with patch.object(
        GeminiModelManager, "_get_or_create_model", return_value=mock_model
    ) as mock_create, patch.object(
        GeminiModelManager, "_get_config_key", return_value="key"
    ):
        mgr = GeminiModelManager.__new__(GeminiModelManager)
        mgr._models = {}
        mgr._model_lock = MagicMock()
        mgr._model_lock.__enter__ = MagicMock(return_value=None)
        mgr._model_lock.__exit__ = MagicMock(return_value=False)
        mgr.model_name = "gemini-2.5-flash"
        mgr.api_key = "test"

        mgr.get_model_for_purpose(purpose=GeminiModelPurpose.BARCODE)

        # Check temperature=0.1 was passed to create
        call_args = mock_create.call_args
        assert call_args[0][1] == 0.1  # temperature positional arg
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/unit/infra/services/ai/providers/test_gemini_provider.py::test_purpose_temperatures_defined -v
```
Expected: `FAILED` — `PURPOSE_TEMPERATURES` not in module yet.

- [ ] **Step 3: Add PURPOSE_TEMPERATURES to gemini_model_config.py**

After the `PURPOSE_ENV_VARS` block, add:

```python
# src/infra/services/ai/gemini_model_config.py

PURPOSE_TEMPERATURES: dict[GeminiModelPurpose, float] = {
    GeminiModelPurpose.GENERAL:    0.2,
    GeminiModelPurpose.MEAL_NAMES: 0.7,  # diversity is the point
    GeminiModelPurpose.RECIPE:     0.4,
    GeminiModelPurpose.BARCODE:    0.1,  # extraction — accuracy over creativity
}
```

- [ ] **Step 4: Update get_model_for_purpose signature and temperature lookup**

In `src/infra/services/ai/gemini_model_manager.py`, update the `get_model_for_purpose` method signature and body:

```python
from src.infra.services.ai.gemini_model_config import (
    GeminiModelPurpose,
    PURPOSE_MODEL_DEFAULTS,
    PURPOSE_ENV_VARS,
    PURPOSE_TEMPERATURES,
)

def get_model_for_purpose(
    self,
    purpose: GeminiModelPurpose = GeminiModelPurpose.GENERAL,
    temperature: Optional[float] = None,   # None = use PURPOSE_TEMPERATURES lookup
    max_output_tokens: Optional[int] = None,
    response_mime_type: Optional[str] = None,
    **kwargs,
):
    """Get model instance configured for specific purpose."""
    if temperature is None:
        temperature = PURPOSE_TEMPERATURES.get(purpose, 0.4)

    env_var = PURPOSE_ENV_VARS.get(purpose, "GEMINI_MODEL")
    model_name = os.getenv(
        env_var, PURPOSE_MODEL_DEFAULTS.get(purpose, self.model_name)
    )

    if purpose in (GeminiModelPurpose.RECIPE, GeminiModelPurpose.BARCODE):
        kwargs.setdefault("thinking_budget", 0)

    config_key = self._get_config_key(
        model_name=model_name,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_mime_type=response_mime_type,
        **kwargs,
    )
    with self._model_lock:
        return self._get_or_create_model(
            config_key,
            model_name,
            temperature,
            max_output_tokens,
            response_mime_type,
            **kwargs,
        )
```

- [ ] **Step 5: Run tests**

```
pytest tests/unit/infra/services/ai/providers/test_gemini_provider.py -v
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/infra/services/ai/gemini_model_config.py \
        src/infra/services/ai/gemini_model_manager.py \
        tests/unit/infra/services/ai/providers/test_gemini_provider.py
git commit -m "feat: add per-purpose temperature calibration

Barcode/text extraction: 0.1 (accuracy over creativity)
Recipe generation: 0.4 (balanced)
Meal name generation: 0.7 (kept — diversity is the point)
General: 0.2

Reduces hallucination on structured JSON tasks, fewer parse retries.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Fix thinking budget routing (Bug 1)

**Why:** `gemini_provider.py` derives `GeminiModelPurpose` from the model string via `MODEL_PURPOSE_MAP`. Both `gemini-2.5-flash` and recipe calls resolve to `GENERAL`, so `thinking_budget=0` is never applied to recipes. Fix: pass the original `ModelPurpose` as a string hint so `GeminiProvider` can resolve the correct Gemini purpose.

**Files:**
- Modify: `src/infra/services/ai/ai_model_manager.py`
- Modify: `src/infra/services/ai/providers/gemini_provider.py`
- Test: `tests/unit/infra/services/ai/providers/test_gemini_provider.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/services/ai/providers/test_gemini_provider.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.infra.services.ai.providers.gemini_provider import GeminiProvider


@pytest.mark.asyncio
async def test_recipe_purpose_hint_disables_thinking():
    """purpose_hint='recipe' must resolve to GeminiModelPurpose.RECIPE,
    which triggers thinking_budget=0 in get_model_for_purpose."""
    provider = GeminiProvider.__new__(GeminiProvider)
    mock_manager = MagicMock()
    mock_manager.get_model_for_purpose = MagicMock(return_value=MagicMock(
        invoke=MagicMock(return_value=MagicMock(content='{"emoji": "🍚"}'))
    ))
    provider._model_manager = mock_manager

    with patch.object(provider, "_extract_json", return_value={"emoji": "🍚"}):
        await provider.generate(
            model="gemini-2.5-flash",
            prompt="test",
            system_message="system",
            purpose_hint="recipe",
        )

    call_kwargs = mock_manager.get_model_for_purpose.call_args
    from src.infra.services.ai.gemini_model_config import GeminiModelPurpose
    assert call_kwargs[1]["purpose"] == GeminiModelPurpose.RECIPE


@pytest.mark.asyncio
async def test_no_purpose_hint_falls_back_to_model_map():
    """Without purpose_hint, MODEL_PURPOSE_MAP is used (backward compat)."""
    provider = GeminiProvider.__new__(GeminiProvider)
    mock_manager = MagicMock()
    mock_manager.get_model_for_purpose = MagicMock(return_value=MagicMock(
        invoke=MagicMock(return_value=MagicMock(content='{"result": "ok"}'))
    ))
    provider._model_manager = mock_manager

    with patch.object(provider, "_extract_json", return_value={"result": "ok"}):
        await provider.generate(
            model="gemini-2.5-flash",
            prompt="test",
            system_message="system",
            # no purpose_hint
        )

    call_kwargs = mock_manager.get_model_for_purpose.call_args
    from src.infra.services.ai.gemini_model_config import GeminiModelPurpose
    assert call_kwargs[1]["purpose"] == GeminiModelPurpose.GENERAL
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/unit/infra/services/ai/providers/test_gemini_provider.py::test_recipe_purpose_hint_disables_thinking -v
```
Expected: `FAILED` — `generate()` doesn't accept `purpose_hint` yet.

- [ ] **Step 3: Update gemini_provider.py — add _PURPOSE_HINT_MAP and purpose_hint**

```python
# src/infra/services/ai/providers/gemini_provider.py

# Replace MODEL_PURPOSE_MAP (kept as fallback) and add _PURPOSE_HINT_MAP:

MODEL_PURPOSE_MAP = {
    "gemini-2.5-flash":      GeminiModelPurpose.GENERAL,
    "gemini-2.5-flash-lite": GeminiModelPurpose.MEAL_NAMES,
}

_PURPOSE_HINT_MAP: dict[str, GeminiModelPurpose] = {
    "recipe":          GeminiModelPurpose.RECIPE,
    "barcode":         GeminiModelPurpose.BARCODE,
    "meal_names":      GeminiModelPurpose.MEAL_NAMES,
    "discovery":       GeminiModelPurpose.MEAL_NAMES,
    "parse_text":      GeminiModelPurpose.GENERAL,
    "ingredient_scan": GeminiModelPurpose.GENERAL,
    "meal_scan":       GeminiModelPurpose.GENERAL,
    "general":         GeminiModelPurpose.GENERAL,
}


class GeminiProvider(AIProviderPort):
    # ... (unchanged)

    async def generate(
        self,
        model: str,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: Optional[int] = None,
        schema: Optional[type] = None,
        purpose_hint: Optional[str] = None,  # NEW: ModelPurpose.value string
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate text using Gemini."""
        if purpose_hint is not None:
            purpose = _PURPOSE_HINT_MAP.get(purpose_hint, GeminiModelPurpose.GENERAL)
        else:
            purpose = MODEL_PURPOSE_MAP.get(model, GeminiModelPurpose.GENERAL)

        response_mime_type = None
        if not schema and response_type == "json":
            response_mime_type = "application/json"

        llm = self._model_manager.get_model_for_purpose(
            purpose=purpose,
            max_output_tokens=max_tokens,
            response_mime_type=response_mime_type,
        )
        # ... rest of method unchanged
```

- [ ] **Step 4: Update ai_model_manager.py — pass purpose_hint to provider**

In the `generate()` method, add `purpose_hint=purpose.value` to the provider call:

```python
# src/infra/services/ai/ai_model_manager.py
# Inside generate(), the provider.generate() call:

result = await provider.generate(
    model=model,
    prompt=prompt,
    system_message=system_message,
    response_type=response_type,
    max_tokens=max_tokens,
    schema=schema,
    purpose_hint=purpose.value,   # NEW
    **kwargs,
)
```

- [ ] **Step 5: Run tests**

```
pytest tests/unit/infra/services/ai/providers/test_gemini_provider.py -v
pytest tests/unit/infra/services/ai/test_ai_model_manager.py -v
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/infra/services/ai/providers/gemini_provider.py \
        src/infra/services/ai/ai_model_manager.py \
        tests/unit/infra/services/ai/providers/test_gemini_provider.py
git commit -m "fix: route purpose hint to GeminiProvider to correctly disable thinking

MODEL_PURPOSE_MAP mapped 'gemini-2.5-flash' → GENERAL regardless of call purpose,
so thinking_budget=0 was never applied to recipe calls. At 2000-4000 hidden thinking
tokens per call, this silently doubled recipe costs.

Fix: pass ModelPurpose.value as purpose_hint through the call chain so
GeminiProvider resolves the correct GeminiModelPurpose.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Fix output token limits

**Why:** Recipe calls cap at 4000 tokens but worst-case output is ~600 tokens (2× headroom at 1200). Vision calls cap at 4096 tokens but output is ~500 tokens. Over-allocation holds connections open, amplifies 503 spikes, and over-bills.

**Files:**
- Modify: `src/domain/services/meal_suggestion/recipe_attempt_builder.py` (line 30)
- Modify: `src/infra/adapters/vision_ai_service.py` (both `generate_with_vision` calls)
- Test: `tests/unit/infra/adapters/test_vision_ai_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/infra/adapters/test_vision_ai_service.py
# Add these tests to the existing file:

def test_vision_analyze_passes_max_tokens_1024(mock_ai_manager, vision_service):
    """Vision calls must pass max_tokens=1024, not use the 4096 default."""
    mock_ai_manager.generate_with_vision = AsyncMock(return_value={"dish_name": "test"})
    strategy = BasicAnalysisStrategy()
    vision_service.analyze_with_strategy(b"fake_image", strategy)
    call_kwargs = mock_ai_manager.generate_with_vision.call_args[1]
    assert call_kwargs.get("max_tokens") == 1024


def test_recipe_token_limit_is_1200():
    """PARALLEL_SINGLE_MEAL_TOKENS must be 1200, not 4000."""
    from src.domain.services.meal_suggestion.recipe_attempt_builder import (
        PARALLEL_SINGLE_MEAL_TOKENS,
    )
    assert PARALLEL_SINGLE_MEAL_TOKENS == 1200
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/infra/adapters/test_vision_ai_service.py::test_vision_analyze_passes_max_tokens_1024 -v
```
Expected: `FAILED` — currently no `max_tokens` is passed in vision calls.

- [ ] **Step 3: Fix recipe token limit**

In `src/domain/services/meal_suggestion/recipe_attempt_builder.py` line 30:

```python
PARALLEL_SINGLE_MEAL_TOKENS = 1200  # was 4000; worst-case output ~600 tokens
```

- [ ] **Step 4: Fix vision token limit in vision_ai_service.py**

Find both calls to `self._ai_manager.generate_with_vision(...)` (around lines 144–151 and 181–187) and add `max_tokens=1024`:

```python
# First call (analyze_with_strategy):
result = self._run_async(
    self._ai_manager.generate_with_vision(
        purpose=ModelPurpose.MEAL_SCAN,
        prompt=strategy.get_user_message(),
        image_data=image_bytes,
        system_message=strategy.get_analysis_prompt(),
        max_tokens=1024,   # NEW: was using 4096 default in gemini_provider.py
    )
)

# Second call (analyze_by_url_with_strategy):
result = self._run_async(
    self._ai_manager.generate_with_vision(
        purpose=ModelPurpose.MEAL_SCAN,
        prompt=strategy.get_user_message(),
        image_data=image_url.encode("utf-8"),
        system_message=strategy.get_analysis_prompt(),
        max_tokens=1024,   # NEW
    )
)
```

- [ ] **Step 5: Run tests**

```
pytest tests/unit/infra/adapters/test_vision_ai_service.py -v
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/domain/services/meal_suggestion/recipe_attempt_builder.py \
        src/infra/adapters/vision_ai_service.py \
        tests/unit/infra/adapters/test_vision_ai_service.py
git commit -m "fix: reduce output token limits to match actual response sizes

Recipe: 4000 → 1200 (worst-case output ~600 tokens, 2x safety margin)
Vision: 4096 → 1024 (worst-case output ~500 tokens, 2x safety margin)

Over-allocation was holding HTTP connections open unnecessarily and
amplifying 503 spikes during parallel recipe generation.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Remove Mistral and Kimi providers

**Why:** Mistral was primary for all text tasks (barcode, text parsing, meal names, discovery) but Gemini Flash-Lite is cheaper and already in the fallback chain. Kimi is unused. Removing both simplifies the provider layer and eliminates any residual Mistral API costs.

**Files:**
- Delete: `src/infra/services/ai/providers/mistral_provider.py`
- Delete: `src/infra/services/ai/providers/kimi_provider.py`
- Modify: `src/infra/services/ai/ai_model_manager.py`
- Test: `tests/unit/infra/services/ai/test_ai_model_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/services/ai/test_ai_model_manager.py
# Add to class TestModelSelection:

def test_no_mistral_in_any_fallback_chain(self, manager):
    """No fallback chain should reference Mistral after removal."""
    from src.infra.services.ai.ai_model_manager import FALLBACK_CHAINS
    all_models = [m for chain in FALLBACK_CHAINS.values() for m in chain]
    assert not any("mistral" in m for m in all_models)

def test_no_kimi_in_any_fallback_chain(self, manager):
    from src.infra.services.ai.ai_model_manager import FALLBACK_CHAINS
    all_models = [m for chain in FALLBACK_CHAINS.values() for m in chain]
    assert not any("kimi" in m for m in all_models)
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/infra/services/ai/test_ai_model_manager.py::TestModelSelection::test_no_mistral_in_any_fallback_chain -v
```
Expected: `FAILED` — Mistral is still in FALLBACK_CHAINS.

- [ ] **Step 3: Update ai_model_manager.py — remove Mistral**

Remove the import:
```python
# DELETE this line:
from src.infra.services.ai.providers.mistral_provider import MistralProvider
```

Update `__init__`:
```python
def __init__(self) -> None:
    self._circuit_breaker = ProviderCircuitBreaker()
    self._gemini = GeminiProvider()
    self._providers = {"gemini": self._gemini}
```

Update `_get_provider_for_model`:
```python
def _get_provider_for_model(self, model: str):
    """Get provider that owns a model."""
    if model.startswith("gemini"):
        return self._gemini
    return None
```

Remove the Mistral availability log lines from `__init__` (the `if self._mistral.is_available()` block).

Also remove all `"mistral-large-latest"` and `"mistral-small-latest"` from FALLBACK_CHAINS (already updated in Task 1, but double-check MEAL_SCAN and INGREDIENT_SCAN chains).

- [ ] **Step 4: Delete provider files**

```bash
rm src/infra/services/ai/providers/mistral_provider.py
rm src/infra/services/ai/providers/kimi_provider.py
```

- [ ] **Step 5: Run full test suite**

```
pytest tests/unit/ -v
```
Expected: all pass. If any test imports `MistralProvider` or `KimiProvider`, update it to remove the import.

- [ ] **Step 6: Commit**

```bash
git add src/infra/services/ai/ai_model_manager.py \
        tests/unit/infra/services/ai/test_ai_model_manager.py
git rm src/infra/services/ai/providers/mistral_provider.py \
       src/infra/services/ai/providers/kimi_provider.py
git commit -m "feat: remove Mistral and Kimi providers

Gemini Flash-Lite handles all text tasks at lower cost.
Mistral was primary for barcode/text/meal-names but Flash-Lite is cheaper
and already in the fallback chain. Kimi was unused.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 2 — Prompt Architecture

### Task 6: Consolidate rules in prompt_constants.py

**Why:** Decomposition rules, emoji rules, and macro accuracy rules are duplicated 3–4 times across `meal_analysis_strategy.py`, `system_prompts.py`, and `prompt_constants.py`. Every fix must be applied in 4 places. Make `prompt_constants.py` the single source of truth and delete the duplicates.

**Files:**
- Modify: `src/domain/strategies/meal_analysis_strategy.py`
- Modify: `src/domain/services/prompts/prompt_constants.py`

- [ ] **Step 1: Check what SCAN_DECOMPOSITION_RULES and BASIC_SCAN_DECOMPOSITION_RULES look like**

```
grep -n "SCAN_DECOMPOSITION_RULES\|BASIC_SCAN_DECOMPOSITION_RULES" \
  src/domain/strategies/meal_analysis_strategy.py
```

Note down the content. You'll merge any unique additions into `prompt_constants.py`.

- [ ] **Step 2: Add a VISION_DECOMPOSITION_RULES constant to prompt_constants.py**

Open `src/domain/services/prompts/prompt_constants.py` and add after the existing `DECOMPOSITION_RULES`:

```python
# Vision-specific decomposition rules (used by all 5 analysis strategies)
VISION_DECOMPOSITION_RULES = (
    "DECOMPOSITION (MANDATORY): For ANY multi-ingredient dish, ALWAYS list "
    "individual ingredients with separate nutritional data. Never return a "
    "single entry for a compound dish. Minimum 3 ingredients per dish.\n"
    "Simple single-ingredient foods (banana, egg, plain rice) stay as 1 item.\n"
    "All quantities in GRAMS where possible."
)
```

- [ ] **Step 3: Remove SCAN_DECOMPOSITION_RULES and BASIC_SCAN_DECOMPOSITION_RULES from meal_analysis_strategy.py**

At the top of `src/domain/strategies/meal_analysis_strategy.py`, find the two constant definitions and replace with imports:

```python
# DELETE: SCAN_DECOMPOSITION_RULES = "..." (multi-line string constant)
# DELETE: BASIC_SCAN_DECOMPOSITION_RULES = "..." (multi-line string constant)

# ADD at the top of the file with other imports:
from src.domain.services.prompts.prompt_constants import VISION_DECOMPOSITION_RULES

# Then in each get_analysis_prompt() that used SCAN_DECOMPOSITION_RULES:
# Replace: ) + SCAN_DECOMPOSITION_RULES
# With:    ) + VISION_DECOMPOSITION_RULES

# And in BasicAnalysisStrategy:
# Replace: ) + BASIC_SCAN_DECOMPOSITION_RULES
# With:    ) + VISION_DECOMPOSITION_RULES
```

- [ ] **Step 4: Run tests**

```
pytest tests/unit/ -v -k "vision or strategy or analysis"
```
Expected: all pass — behavior is identical, just the source of the constant changed.

- [ ] **Step 5: Commit**

```bash
git add src/domain/strategies/meal_analysis_strategy.py \
        src/domain/services/prompts/prompt_constants.py
git commit -m "refactor: consolidate decomposition rules to prompt_constants.py

Removed SCAN_DECOMPOSITION_RULES and BASIC_SCAN_DECOMPOSITION_RULES
from meal_analysis_strategy.py. All 5 vision strategies now import
VISION_DECOMPOSITION_RULES from the single source of truth.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Add RECIPE_GENERATION system prompt to SystemPrompts

**Why:** Three copies of an inline recipe system string exist in `parallel_recipe_generator.py`. They're short (~100 tokens) and don't include few-shot examples. Replacing with a ≥1024-token system prompt enables Gemini implicit caching AND reduces parse failures via few-shot examples.

**Files:**
- Modify: `src/infra/services/ai/prompts/system_prompts.py`

- [ ] **Step 1: Add RECIPE_GENERATION constant**

Open `src/infra/services/ai/prompts/system_prompts.py` and add after the existing constants:

```python
# src/infra/services/ai/prompts/system_prompts.py

RECIPE_GENERATION = """You are a professional chef and nutritionist. Generate complete, accurate recipes as JSON only. No markdown, no prose, no commentary.

RESPONSE FORMAT — return exactly this structure:
{
  "emoji": "🍚",
  "cuisine_type": "Vietnamese",
  "origin_country": "Vietnam",
  "ingredients": [
    {"name": "chicken breast", "amount": 200, "unit": "g"},
    {"name": "jasmine rice", "amount": 150, "unit": "g"},
    {"name": "broccoli", "amount": 100, "unit": "g"},
    {"name": "soy sauce", "amount": 15, "unit": "g"},
    {"name": "sesame oil", "amount": 5, "unit": "g"}
  ],
  "recipe_steps": [
    {"step": 1, "instruction": "Season chicken breast with salt and pepper.", "duration_minutes": 2},
    {"step": 2, "instruction": "Cook chicken over medium heat for 6 minutes per side until cooked through.", "duration_minutes": 14},
    {"step": 3, "instruction": "Steam broccoli for 4 minutes until tender-crisp.", "duration_minutes": 5},
    {"step": 4, "instruction": "Serve chicken and broccoli over rice. Drizzle with soy sauce and sesame oil.", "duration_minutes": 2}
  ],
  "prep_time_minutes": 23
}

INGREDIENT RULES:
- ALL ingredients MUST have exact gram amounts. No bare items without amounts.
- Typical ranges: lean protein 150-250g, grain 100-200g, vegetables 80-150g, oil 5-15g, sauce 10-20g.
- Minimum 3 ingredients, maximum 8 ingredients per recipe.
- Do NOT invent ingredients not associated with the dish name.
- ALL ingredient names MUST be in ENGLISH ONLY — no Vietnamese, Japanese, or any non-English text.

DECOMPOSITION RULES:
- ALWAYS break compound dishes into individual raw ingredients. Never return a single entry for a multi-ingredient dish.
- "Pho bo" → rice noodles (200g) + beef slices (100g) + broth (400g) + bean sprouts (50g) + herbs (20g)
- "Pasta carbonara" → spaghetti (180g) + bacon (60g) + egg (50g) + parmesan (30g) + cream (30g)
- Every multi-ingredient dish must have ≥3 separate ingredient entries.
- Simple foods (plain banana, boiled egg, plain white rice) may be a single entry.

SCALING RULES:
- Size ALL quantities for the specified serving count only.
- 1 serving of cooked rice = ~150g. 2 servings = 300g. Never use bulk amounts for single servings.
- When target says "1 serving", every gram amount is portioned for exactly one person.

RECIPE STEP RULES:
- 2 to 6 steps only.
- Each step must start with a clear action verb: Season, Cook, Steam, Grill, Combine, Slice, Serve.
- Each step must include a realistic duration in minutes.
- Steps must be sequential — each builds on the previous.

EMOJI SELECTION — return exactly ONE emoji based on serving style:
  🍜 noodle soup (pho, ramen, bun bo) | 🍝 dry pasta or noodles
  🍚 rice dishes | 🍛 curry over rice | 🍲 stew, hotpot, thick soup
  🥗 salad or fresh bowl | 🍖 grilled meat | 🥘 braised or simmered
  🥟 dumplings or spring rolls | 🥪 sandwich or banh mi | 🍳 egg dishes
  🥣 porridge or congee | 🍗 fried chicken | 🥩 steak or pan-seared meat

CALORIE ACCURACY:
- Verify your numbers: calories ≈ protein*4 + carbs*4 + fat*9 (±10%)
- Fat must be ≥3g for any real cooked dish. Pure lean protein + plain veg combos: ≥5g fat.
- If the target calorie count is ≤400, use lean portions: 80-140g lean protein, plenty of vegetables, small starch (50-80g), 0-5g added fat/oil.

---

WORKED EXAMPLE 1 — "Grilled Chicken Caesar Salad" (target: 420 cal, 1 serving):
{
  "emoji": "🥗",
  "cuisine_type": "Italian-American",
  "origin_country": "United States",
  "ingredients": [
    {"name": "chicken breast", "amount": 180, "unit": "g"},
    {"name": "romaine lettuce", "amount": 100, "unit": "g"},
    {"name": "cherry tomatoes", "amount": 80, "unit": "g"},
    {"name": "parmesan cheese", "amount": 20, "unit": "g"},
    {"name": "caesar dressing", "amount": 25, "unit": "g"},
    {"name": "olive oil", "amount": 8, "unit": "g"}
  ],
  "recipe_steps": [
    {"step": 1, "instruction": "Season chicken breast with salt, pepper, and garlic powder.", "duration_minutes": 2},
    {"step": 2, "instruction": "Grill chicken over medium-high heat for 6 minutes per side until internal temperature reaches 165F. Rest 3 minutes then slice thin.", "duration_minutes": 16},
    {"step": 3, "instruction": "Tear romaine into bite-sized pieces. Halve cherry tomatoes. Arrange in a bowl.", "duration_minutes": 3},
    {"step": 4, "instruction": "Toss greens and tomatoes with caesar dressing and olive oil. Top with sliced chicken and shaved parmesan.", "duration_minutes": 2}
  ],
  "prep_time_minutes": 23
}

WORKED EXAMPLE 2 — "Beef Fried Rice" (target: 510 cal, 1 serving):
{
  "emoji": "🍚",
  "cuisine_type": "Chinese",
  "origin_country": "China",
  "ingredients": [
    {"name": "cooked white rice", "amount": 180, "unit": "g"},
    {"name": "beef sirloin strips", "amount": 120, "unit": "g"},
    {"name": "whole egg", "amount": 50, "unit": "g"},
    {"name": "frozen mixed vegetables", "amount": 80, "unit": "g"},
    {"name": "soy sauce", "amount": 15, "unit": "g"},
    {"name": "sesame oil", "amount": 5, "unit": "g"},
    {"name": "garlic cloves", "amount": 8, "unit": "g"}
  ],
  "recipe_steps": [
    {"step": 1, "instruction": "Marinate beef strips in 8g soy sauce for 5 minutes.", "duration_minutes": 5},
    {"step": 2, "instruction": "Heat wok over high heat. Stir-fry beef 2-3 minutes until browned. Remove and set aside.", "duration_minutes": 4},
    {"step": 3, "instruction": "In same wok, scramble egg for 1 minute. Add minced garlic and vegetables, stir-fry 2 minutes.", "duration_minutes": 4},
    {"step": 4, "instruction": "Add cold rice, break up any clumps, stir-fry 3 minutes until heated through and slightly crisp.", "duration_minutes": 4},
    {"step": 5, "instruction": "Return beef to wok. Add remaining soy sauce and sesame oil. Toss everything together and serve.", "duration_minutes": 2}
  ],
  "prep_time_minutes": 19
}

Return ONLY valid JSON matching the structure above. No additional keys. No markdown. No explanation."""
```

> **Note:** Verify this prompt is ≥1024 tokens using the Gemini `countTokens` API before deploying Phase 3 caching. This is listed as Open Question #1 in the spec.

- [ ] **Step 2: Verify RECIPE_GENERATION is accessible**

```
python -c "from src.infra.services.ai.prompts.system_prompts import SystemPrompts; print(len(SystemPrompts.RECIPE_GENERATION.split()))"
```
Expected: ≥700 words printed (rough proxy for ≥1024 tokens).

- [ ] **Step 3: Commit**

```bash
git add src/infra/services/ai/prompts/system_prompts.py
git commit -m "feat: add RECIPE_GENERATION system prompt with few-shot examples

Centralises the recipe system message (was duplicated 3x inline).
Includes 2 worked examples for parse reliability.
≥1024 tokens for Gemini implicit caching eligibility.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Add VISION_ANALYSIS system prompt + modernise 4 strategies

**Why:** `PortionAware`, `IngredientAware`, `WeightAware`, and `UserContextAware` strategies still use verbose 15-line `get_analysis_prompt()` methods and append `SCAN_DECOMPOSITION_RULES`. `BasicAnalysisStrategy` was already optimised. All 5 strategies should share one static system message so there's exactly one cache entry for all vision calls.

**Files:**
- Modify: `src/infra/services/ai/prompts/system_prompts.py`
- Modify: `src/domain/strategies/meal_analysis_strategy.py`
- Test: `tests/unit/infra/adapters/test_vision_ai_service.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/domain/strategies/test_meal_analysis_strategy.py (create if not exists)
import pytest
from src.domain.strategies.meal_analysis_strategy import (
    BasicAnalysisStrategy,
    PortionAwareAnalysisStrategy,
    IngredientAwareAnalysisStrategy,
    WeightAwareAnalysisStrategy,
    UserContextAwareAnalysisStrategy,
)
from src.infra.services.ai.prompts.system_prompts import SystemPrompts


def test_all_strategies_return_same_system_prompt():
    """All 5 vision strategies must return SystemPrompts.VISION_ANALYSIS as their system prompt."""
    strategies = [
        BasicAnalysisStrategy(),
        PortionAwareAnalysisStrategy(350.0, "g"),
        IngredientAwareAnalysisStrategy([{"name": "rice", "quantity": 200, "unit": "g"}]),
        WeightAwareAnalysisStrategy(350.0),
        UserContextAwareAnalysisStrategy({"goal": "lose_weight"}),
    ]
    for s in strategies:
        assert s.get_analysis_prompt() == SystemPrompts.VISION_ANALYSIS, (
            f"{s.__class__.__name__}.get_analysis_prompt() must return SystemPrompts.VISION_ANALYSIS"
        )


def test_portion_aware_user_message_is_compact():
    """PortionAwareAnalysisStrategy user message must be ≤3 lines."""
    s = PortionAwareAnalysisStrategy(350.0, "g")
    msg = s.get_user_message()
    assert "350" in msg and "g" in msg
    assert len(msg.splitlines()) <= 3
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/domain/strategies/test_meal_analysis_strategy.py -v
```
Expected: `FAILED` — strategies don't return `SystemPrompts.VISION_ANALYSIS` yet.

- [ ] **Step 3: Add VISION_ANALYSIS to SystemPrompts**

Open `src/infra/services/ai/prompts/system_prompts.py` and add:

```python
VISION_ANALYSIS = """You are a nutrition analysis assistant. Analyze food images and return structured nutritional data as JSON only. No markdown, no prose.

RESPONSE FORMAT — return exactly this structure:
{
  "dish_name": "Overall dish name or comma-separated items if complex",
  "emoji": "single food emoji that best represents this dish",
  "foods": [
    {
      "name": "Food name in English",
      "quantity": 150.0,
      "unit": "g",
      "calories": 248,
      "macros": {"protein": 46.0, "carbs": 0.0, "fat": 5.5}
    }
  ],
  "total_calories": 248,
  "confidence": 0.85
}

IDENTIFICATION RULES:
- Identify every visible distinct food component in the image.
- Maximum 8 food items. If more are visible, group minor garnishes.
- Use common English names: "white rice", "chicken breast", "broccoli florets".
- If the image shows a single-serve plated dish, treat it as one portion.

DECOMPOSITION RULES:
- ALWAYS break compound dishes into individual ingredients with separate entries.
- "Pho" → rice noodles + beef slices + broth + bean sprouts + herbs
- "Fried rice" → rice + protein + vegetables + egg + oil
- "Sandwich" → bread + protein + cheese + vegetables + condiment
- Simple single-ingredient foods (plain banana, hard-boiled egg) stay as 1 entry.
- Minimum 3 entries for any multi-ingredient dish.

QUANTITY ESTIMATION:
- Estimate quantities in grams based on visual portion size.
- Use standard reference sizes: 1 cup cooked rice ≈ 180g, 1 chicken breast ≈ 170g, 1 egg ≈ 50g.
- For liquids/sauces, estimate by the ml they appear to occupy, then convert to grams.
- All quantities must be realistic for what is visually present.

NUTRITION CALCULATION:
- Calculate macros from standard food databases per 100g.
- Calories must match: calories ≈ protein*4 + carbs*4 + fat*9 (±5%).
- All macro values in grams. Confidence between 0.0 (guessing) and 1.0 (clear image, known food).
- Fat must be ≥0.5g for any cooked or dressed food. Pure raw vegetables: fat may be 0.

EMOJI SELECTION — one emoji for the overall dish:
  🍜 noodle soup | 🍝 dry pasta/noodles | 🍚 rice dish | 🍛 curry
  🍲 stew/hotpot | 🥗 salad/bowl | 🍖 grilled meat | 🥘 braised
  🥟 dumplings/rolls | 🥪 sandwich | 🍳 eggs | 🥣 porridge | 🍗 fried chicken

---

WORKED EXAMPLE — Chicken rice bowl image:
{
  "dish_name": "Grilled Chicken Rice Bowl",
  "emoji": "🍚",
  "foods": [
    {"name": "cooked white rice", "quantity": 180.0, "unit": "g", "calories": 234, "macros": {"protein": 4.3, "carbs": 51.0, "fat": 0.4}},
    {"name": "grilled chicken breast", "quantity": 150.0, "unit": "g", "calories": 248, "macros": {"protein": 46.5, "carbs": 0.0, "fat": 5.4}},
    {"name": "steamed broccoli", "quantity": 80.0, "unit": "g", "calories": 27, "macros": {"protein": 2.8, "carbs": 5.6, "fat": 0.3}},
    {"name": "soy sauce", "quantity": 10.0, "unit": "g", "calories": 6, "macros": {"protein": 1.0, "carbs": 0.8, "fat": 0.0}}
  ],
  "total_calories": 515,
  "confidence": 0.88
}

Return ONLY valid JSON matching the structure above."""
```

- [ ] **Step 4: Modernise the 4 verbose strategies in meal_analysis_strategy.py**

For each of `PortionAwareAnalysisStrategy`, `IngredientAwareAnalysisStrategy`, `WeightAwareAnalysisStrategy`, `UserContextAwareAnalysisStrategy`, replace the verbose `get_analysis_prompt()` with:

```python
def get_analysis_prompt(self) -> str:
    from src.infra.services.ai.prompts.system_prompts import SystemPrompts
    return SystemPrompts.VISION_ANALYSIS
```

And simplify each `get_user_message()` to the compact dynamic-only version:

**PortionAwareAnalysisStrategy:**
```python
def get_user_message(self) -> str:
    return (
        f"Analyze this food image.\n"
        f"Portion context: {self.portion_size} {self.unit}. "
        f"Scale all nutrition values to match this portion."
    )
```

**IngredientAwareAnalysisStrategy:**
```python
def get_user_message(self) -> str:
    ing_str = ", ".join(
        f"{i.get('name', '')} ({i.get('quantity', '')} {i.get('unit', '')})"
        for i in self.ingredients[:6]
    )
    return (
        f"Analyze this food image.\n"
        f"Known ingredients: {ing_str}. "
        f"Use this context to improve accuracy."
    )
```

**WeightAwareAnalysisStrategy:**
```python
def get_user_message(self) -> str:
    return (
        f"Analyze this food image.\n"
        f"Total weight: {self.total_weight}g. "
        f"Scale all nutrition values proportionally to this total weight."
    )
```

**UserContextAwareAnalysisStrategy:**
```python
def get_user_message(self) -> str:
    goal = self.user_context.get("goal", "balanced nutrition")
    return (
        f"Analyze this food image.\n"
        f"User goal: {goal}. "
        f"Provide accurate nutrition data for this meal."
    )
```

Also update `BasicAnalysisStrategy.get_analysis_prompt()` to use the shared constant:
```python
def get_analysis_prompt(self) -> str:
    from src.infra.services.ai.prompts.system_prompts import SystemPrompts
    return SystemPrompts.VISION_ANALYSIS
```

- [ ] **Step 5: Run tests**

```
pytest tests/unit/domain/strategies/test_meal_analysis_strategy.py -v
pytest tests/unit/infra/adapters/test_vision_ai_service.py -v
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/infra/services/ai/prompts/system_prompts.py \
        src/domain/strategies/meal_analysis_strategy.py \
        tests/unit/domain/strategies/test_meal_analysis_strategy.py
git commit -m "feat: add VISION_ANALYSIS system prompt; modernise all 5 vision strategies

All 5 strategies now return a shared SystemPrompts.VISION_ANALYSIS
(was 4 separate verbose implementations). User messages are compact
dynamic-only content.

Single system prompt = one implicit cache entry for all vision calls.
Includes worked example for parse reliability.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 9: Replace inline recipe system strings in parallel_recipe_generator.py

**Why:** Three methods in `parallel_recipe_generator.py` each define their own inline `recipe_system` string (~100 tokens each). Replace all three with `SystemPrompts.RECIPE_GENERATION`.

**Files:**
- Modify: `src/domain/services/meal_suggestion/parallel_recipe_generator.py`
- Test: `tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py
# Add:

def test_recipe_system_uses_central_constant():
    """Inline recipe_system strings must be gone; SystemPrompts.RECIPE_GENERATION must be used."""
    import inspect
    from src.domain.services.meal_suggestion import parallel_recipe_generator
    source = inspect.getsource(parallel_recipe_generator)
    # The inline string started with "You are a professional chef"
    assert "You are a professional chef. Return ONLY this exact JSON structure" not in source
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest "tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py::test_recipe_system_uses_central_constant" -v
```
Expected: `FAILED` — inline strings still present.

- [ ] **Step 3: Add import and replace all three inline recipe_system definitions**

At the top of `src/domain/services/meal_suggestion/parallel_recipe_generator.py`, add:

```python
from src.infra.services.ai.prompts.system_prompts import SystemPrompts
```

Then search for all three occurrences of the pattern:
```python
recipe_system = (
    "You are a professional chef. Return ONLY this exact JSON structure:\n"
    ...
)
```

Replace each one with:
```python
recipe_system = SystemPrompts.RECIPE_GENERATION
```

There are 3 occurrences: in `_phase2_generate_recipes` (or equivalent), `generate_selected_recipes`, and the streaming path. Verify with:
```
grep -n "recipe_system = " src/domain/services/meal_suggestion/parallel_recipe_generator.py
```
All 3 must now read `recipe_system = SystemPrompts.RECIPE_GENERATION`.

- [ ] **Step 4: Run tests**

```
pytest tests/unit/domain/services/meal_suggestion/ -v
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/domain/services/meal_suggestion/parallel_recipe_generator.py \
        tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py
git commit -m "refactor: replace 3 inline recipe system strings with SystemPrompts.RECIPE_GENERATION

Single source of truth. Now editing the recipe system prompt is one-line change
in one file instead of hunting three identical strings.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 3 — Observability + Caching

### Task 10: Add PostHog LLM Analytics via OpenTelemetry

**Why:** Zero visibility into per-feature AI cost, token counts, or latency today. PostHog's LLM Analytics auto-instrumentation captures every LangChain call with model, tokens, cost, and latency — zero manual code changes to existing call sites.

**Files:**
- Modify: `requirements.txt`
- Modify: `src/api/main.py`
- Test: smoke test at startup

- [ ] **Step 1: Add packages to requirements.txt**

```
# After the existing langchain-google-genai line, add:
posthog[otel]>=3.0.0
opentelemetry-instrumentation-langchain>=0.1.0
```

- [ ] **Step 2: Install packages**

```bash
pip install "posthog[otel]>=3.0.0" "opentelemetry-instrumentation-langchain>=0.1.0"
```

- [ ] **Step 3: Add OpenTelemetry init to main.py lifespan**

In `src/api/main.py`, add to the top-level imports:

```python
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
```

Then at the START of the `lifespan()` function (before Firebase init), add:

```python
# PostHog LLM Analytics via OpenTelemetry — must run before any LangChain calls
_posthog_key = os.getenv("POSTHOG_API_KEY")
if _posthog_key:
    try:
        from posthog.ai.otel import PostHogSpanProcessor
        from opentelemetry.instrumentation.langchain import LangchainInstrumentor

        _otel_provider = TracerProvider(
            resource=Resource(attributes={SERVICE_NAME: "mealtrack-backend"})
        )
        _otel_provider.add_span_processor(
            PostHogSpanProcessor(
                api_key=_posthog_key,
                host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
            )
        )
        trace.set_tracer_provider(_otel_provider)
        LangchainInstrumentor().instrument()
        logger.info("PostHog LLM Analytics instrumented via OpenTelemetry")
    except Exception as e:
        logger.warning(f"PostHog LLM Analytics init failed (non-fatal): {e}")
else:
    logger.info("POSTHOG_API_KEY not set — LLM analytics disabled")
```

- [ ] **Step 4: Verify startup works**

```bash
uvicorn src.api.main:app --reload
```
Expected: server starts, log line appears:
- With key set: `PostHog LLM Analytics instrumented via OpenTelemetry`
- Without key: `POSTHOG_API_KEY not set — LLM analytics disabled`

No crash either way.

- [ ] **Step 5: Verify PostHog receives events**

Make one recipe generation call from the mobile app or via curl. In PostHog, go to **Events** and filter for `$ai_generation`. You should see an event with `$ai_model`, `$ai_input_tokens`, `$ai_output_tokens`, `$ai_total_cost_usd`.

- [ ] **Step 6: Create PostHog dashboards**

In PostHog UI, create an **Insights** dashboard named "AI Cost Monitoring" with these 5 charts:
1. **Daily AI cost** — `sum($ai_total_cost_usd)` grouped by day
2. **Cost by model** — `sum($ai_total_cost_usd)` broken down by `$ai_model`
3. **Avg tokens per recipe call** — `avg($ai_output_tokens)` filtered to `$ai_model = gemini-2.5-flash-lite`
4. **p95 latency** — `p95($ai_latency)` grouped by `$ai_model`
5. **Output tokens over time** — trend to detect prompt bloat regressions

- [ ] **Step 7: Commit**

```bash
git add requirements.txt src/api/main.py
git commit -m "feat: add PostHog LLM Analytics via OpenTelemetry

Auto-instruments all LangChain calls. Captures model, input_tokens,
output_tokens, cost_usd, and latency for every AI generation.
Gracefully disabled when POSTHOG_API_KEY is not set.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 11: Implement GeminiCacheManager

**Why:** At 1M users, paying full input token price on every call is ~$990/day in input costs for recipes alone. Explicit caching gives 90% discount on the static system prompt portion, reducing that to ~$55/day.

**Files:**
- New: `src/infra/services/ai/gemini_cache_manager.py`
- Modify: `src/api/main.py` (call warm_all on startup)
- Test: `tests/unit/infra/services/ai/test_gemini_cache_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infra/services/ai/test_gemini_cache_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_redis():
    r = MagicMock()
    r.get = MagicMock(return_value=None)
    r.set = MagicMock()
    return r


@pytest.fixture
def cache_manager(mock_redis):
    from src.infra.services.ai.gemini_cache_manager import GeminiCacheManager
    return GeminiCacheManager(redis_client=mock_redis, api_key="test-key")


def test_get_cache_name_returns_none_when_no_cache(cache_manager, mock_redis):
    mock_redis.get.return_value = None
    assert cache_manager.get_cache_name("recipe") is None


def test_get_cache_name_returns_stored_name(cache_manager, mock_redis):
    mock_redis.get.return_value = b"cachedContents/abc123"
    result = cache_manager.get_cache_name("recipe")
    assert result == "cachedContents/abc123"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/unit/infra/services/ai/test_gemini_cache_manager.py -v
```
Expected: `FAILED` — `GeminiCacheManager` module doesn't exist.

- [ ] **Step 3: Create GeminiCacheManager**

```python
# src/infra/services/ai/gemini_cache_manager.py
"""Manages Gemini explicit context cache lifecycle. Singleton."""
import asyncio
import datetime
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_REDIS_KEYS = {
    "recipe":     "gemini_cache:recipe",
    "vision":     "gemini_cache:vision",
    "discovery":  "gemini_cache:discovery",
    "text_parse": "gemini_cache:text_parse",
}

TTL_SECONDS = 3600        # Gemini cache TTL: 1 hour
REFRESH_BEFORE_EXPIRY = 600  # Refresh at 50 min to avoid expiry mid-request


class GeminiCacheManager:
    """Creates and refreshes Gemini explicit context caches.

    Cache names are stored in Redis so all worker processes share one cache ID.
    On Redis miss, falls back to uncached calls — no error raised.
    """

    def __init__(self, redis_client, api_key: Optional[str] = None):
        self._redis = redis_client
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")

    def get_cache_name(self, cache_type: str) -> Optional[str]:
        """Return cache name from Redis, or None if not yet created."""
        redis_key = _CACHE_REDIS_KEYS.get(cache_type)
        if not redis_key:
            return None
        raw = self._redis.get(redis_key)
        if raw is None:
            return None
        return raw.decode("utf-8") if isinstance(raw, bytes) else raw

    def _set_cache_name(self, cache_type: str, name: str) -> None:
        redis_key = _CACHE_REDIS_KEYS[cache_type]
        # TTL slightly longer than cache TTL so Redis key outlives the background refresh window
        self._redis.set(redis_key, name, ex=TTL_SECONDS + REFRESH_BEFORE_EXPIRY)

    async def _create_cache(self, cache_type: str, system_prompt: str, model: str) -> Optional[str]:
        """Create one Gemini explicit cache. Returns cache name or None on failure."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            cache = await asyncio.to_thread(
                genai.caching.CachedContent.create,
                model=f"models/{model}",
                display_name=f"mealtrack_{cache_type}",
                system_instruction=system_prompt,
                ttl=datetime.timedelta(seconds=TTL_SECONDS),
            )
            logger.info(f"[GEMINI-CACHE] Created cache_type={cache_type} name={cache.name}")
            return cache.name
        except Exception as e:
            logger.warning(f"[GEMINI-CACHE] Failed to create cache_type={cache_type}: {e}")
            return None

    async def warm_all(self) -> None:
        """Create all 4 caches at startup. Called from app lifespan."""
        from src.infra.services.ai.prompts.system_prompts import SystemPrompts

        cache_configs = {
            "recipe":     (SystemPrompts.RECIPE_GENERATION, "gemini-2.5-flash"),
            "vision":     (SystemPrompts.VISION_ANALYSIS,   "gemini-2.5-flash"),
            "discovery":  (SystemPrompts.get_meal_text_parsing_prompt(), "gemini-2.5-flash-lite"),
            "text_parse": (SystemPrompts.get_meal_text_parsing_prompt(), "gemini-2.5-flash-lite"),
        }

        tasks = []
        for cache_type, (prompt, model) in cache_configs.items():
            tasks.append(self._warm_one(cache_type, prompt, model))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _warm_one(self, cache_type: str, prompt: str, model: str) -> None:
        existing = self.get_cache_name(cache_type)
        if existing:
            logger.info(f"[GEMINI-CACHE] Already warm: cache_type={cache_type}")
            return
        name = await self._create_cache(cache_type, prompt, model)
        if name:
            self._set_cache_name(cache_type, name)

    async def refresh_loop(self) -> None:
        """Background task: refresh caches before TTL expiry. Run indefinitely."""
        while True:
            await asyncio.sleep(REFRESH_BEFORE_EXPIRY)
            logger.info("[GEMINI-CACHE] Refreshing caches before TTL expiry")
            await self.warm_all()
```

- [ ] **Step 4: Wire warm_all into main.py lifespan**

```python
# src/api/main.py — add after Redis init in lifespan:

# Initialize Gemini explicit context caches (Phase 3)
gemini_cache_manager = None
try:
    from src.infra.services.ai.gemini_cache_manager import GeminiCacheManager
    from src.infra.cache.redis_client import get_redis_client  # use existing Redis accessor

    _redis = get_redis_client()
    gemini_cache_manager = GeminiCacheManager(redis_client=_redis)
    await gemini_cache_manager.warm_all()

    # Background refresh task
    asyncio.create_task(gemini_cache_manager.refresh_loop())
    logger.info("Gemini context caches warmed")
except Exception as e:
    logger.warning(f"Gemini cache warmup failed (non-fatal, uncached calls will be used): {e}")
```

- [ ] **Step 5: Run tests**

```
pytest tests/unit/infra/services/ai/test_gemini_cache_manager.py -v
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/infra/services/ai/gemini_cache_manager.py \
        src/api/main.py \
        tests/unit/infra/services/ai/test_gemini_cache_manager.py
git commit -m "feat: add GeminiCacheManager for explicit context caching

Creates 4 caches at startup (recipe, vision, discovery, text_parse).
Cache names stored in Redis for cross-process sharing.
Background task refreshes at 50min to prevent TTL expiry mid-request.
Falls back to uncached calls on any failure — no degradation.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 12: Wire cached_content into GeminiProvider

**Why:** `GeminiCacheManager` creates the caches but nothing references them yet. Wire the cache name into `GeminiProvider.generate()` so calls with a hot cache pay 90% less on input tokens.

**Files:**
- Modify: `src/infra/services/ai/providers/gemini_provider.py`
- Modify: `src/infra/services/ai/gemini_model_manager.py`
- Test: `tests/unit/infra/services/ai/providers/test_gemini_provider.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/infra/services/ai/providers/test_gemini_provider.py
# Add:

@pytest.mark.asyncio
async def test_generate_passes_cached_content_when_available():
    """When cache_name is provided, get_model_for_purpose receives cached_content kwarg."""
    provider = GeminiProvider.__new__(GeminiProvider)
    mock_manager = MagicMock()
    mock_model = MagicMock()
    mock_model.invoke = MagicMock(return_value=MagicMock(content='{"emoji":"🍚"}'))
    mock_manager.get_model_for_purpose = MagicMock(return_value=mock_model)
    provider._model_manager = mock_manager

    with patch.object(provider, "_extract_json", return_value={"emoji": "🍚"}):
        await provider.generate(
            model="gemini-2.5-flash-lite",
            prompt="Recipe for chicken salad",
            system_message="",          # empty — system is in cache
            purpose_hint="recipe",
            cache_name="cachedContents/abc123",
        )

    call_kwargs = mock_manager.get_model_for_purpose.call_args[1]
    assert call_kwargs.get("cached_content") == "cachedContents/abc123"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest "tests/unit/infra/services/ai/providers/test_gemini_provider.py::test_generate_passes_cached_content_when_available" -v
```
Expected: `FAILED` — `generate()` doesn't accept `cache_name` yet.

- [ ] **Step 3: Update GeminiProvider.generate() to accept and forward cache_name**

```python
# src/infra/services/ai/providers/gemini_provider.py

async def generate(
    self,
    model: str,
    prompt: str,
    system_message: str,
    response_type: str = "json",
    max_tokens: Optional[int] = None,
    schema: Optional[type] = None,
    purpose_hint: Optional[str] = None,
    cache_name: Optional[str] = None,   # NEW: Gemini explicit cache ID
    **kwargs: Any,
) -> Dict[str, Any]:
    if purpose_hint is not None:
        purpose = _PURPOSE_HINT_MAP.get(purpose_hint, GeminiModelPurpose.GENERAL)
    else:
        purpose = MODEL_PURPOSE_MAP.get(model, GeminiModelPurpose.GENERAL)

    response_mime_type = None
    if not schema and response_type == "json":
        response_mime_type = "application/json"

    extra_kwargs = {}
    if cache_name:
        extra_kwargs["cached_content"] = cache_name

    llm = self._model_manager.get_model_for_purpose(
        purpose=purpose,
        max_output_tokens=max_tokens,
        response_mime_type=response_mime_type,
        **extra_kwargs,
    )

    # When using explicit cache the system message is already in the cache —
    # include it only when there's no cache to avoid duplication errors.
    messages = []
    if not cache_name and system_message:
        messages.append(SystemMessage(content=system_message))
    messages.append(HumanMessage(content=prompt))

    # ... rest unchanged
```

- [ ] **Step 4: Update GeminiModelManager._create_model to forward cached_content**

In `src/infra/services/ai/gemini_model_manager.py`, update `_create_model` to pass `cached_content` to `ChatGoogleGenerativeAI` if provided:

```python
def _create_model(
    self,
    temperature: float,
    max_output_tokens: Optional[int],
    response_mime_type: Optional[str],
    model_name: str = None,
    **kwargs,  # includes cached_content if present
):
    from langchain_google_genai import ChatGoogleGenerativeAI

    cfg = {
        "model": model_name or self.model_name,
        "temperature": temperature,
        "google_api_key": self.api_key,
        "convert_system_message_to_human": True,
    }
    if max_output_tokens is not None:
        cfg["max_output_tokens"] = max_output_tokens
    if response_mime_type is not None:
        cfg["response_mime_type"] = response_mime_type
    # Forward cached_content and any other extra kwargs
    cfg.update(
        {k: v for k, v in kwargs.items() if k not in ("google_api_key", "model")}
    )
    return ChatGoogleGenerativeAI(**cfg)
```

- [ ] **Step 5: Update ai_model_manager.generate() to look up and pass cache_name**

In `src/infra/services/ai/ai_model_manager.py`, update the `generate()` method:

```python
async def generate(
    self,
    purpose: ModelPurpose,
    prompt: str,
    system_message: str,
    response_type: str = "json",
    max_tokens: Optional[int] = None,
    schema: Optional[type] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    # Look up explicit cache name for this purpose
    cache_name: Optional[str] = None
    cache_mgr = getattr(self, "_cache_manager", None)
    if cache_mgr is not None:
        purpose_to_cache_type = {
            ModelPurpose.RECIPE:     "recipe",
            ModelPurpose.MEAL_SCAN:  "vision",
            ModelPurpose.DISCOVERY:  "discovery",
            ModelPurpose.PARSE_TEXT: "text_parse",
            ModelPurpose.BARCODE:    "text_parse",
        }
        cache_type = purpose_to_cache_type.get(purpose)
        if cache_type:
            cache_name = cache_mgr.get_cache_name(cache_type)

    # ... existing fallback chain loop, then inside the loop:
    result = await provider.generate(
        model=model,
        prompt=prompt,
        system_message=system_message,
        response_type=response_type,
        max_tokens=max_tokens,
        schema=schema,
        purpose_hint=purpose.value,
        cache_name=cache_name,   # NEW
        **kwargs,
    )
```

Also add a `set_cache_manager()` method to `AIModelManager`:
```python
def set_cache_manager(self, cache_manager) -> None:
    """Wire in GeminiCacheManager. Called from lifespan after warmup."""
    self._cache_manager = cache_manager
```

And call it from `main.py` after `warm_all()`:
```python
AIModelManager.get_instance().set_cache_manager(gemini_cache_manager)
```

- [ ] **Step 6: Run tests**

```
pytest tests/unit/infra/services/ai/ -v
```
Expected: all pass.

- [ ] **Step 7: Verify cache hits in PostHog**

Deploy and wait 5 minutes. In PostHog, open the AI Cost Monitoring dashboard. Look for `$ai_cached_tokens > 0` on recipe calls — that confirms the cache is being hit. Cache hit rate should be ≥85% in steady state.

- [ ] **Step 8: Commit**

```bash
git add src/infra/services/ai/providers/gemini_provider.py \
        src/infra/services/ai/gemini_model_manager.py \
        src/infra/services/ai/ai_model_manager.py \
        src/api/main.py \
        tests/unit/infra/services/ai/providers/test_gemini_provider.py
git commit -m "feat: wire Gemini explicit context cache into generation calls

When GeminiCacheManager has a warm cache for the call's purpose, the
cache name is forwarded to ChatGoogleGenerativeAI as cached_content.
System message is omitted from the messages list when cache is active
(it's already in the cache — passing it again would cause a Gemini error).

Falls back to standard uncached call when cache_manager is None or
cache key is missing from Redis.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Task covering it |
|---|---|
| Bug 1: thinking budget routing | Task 3 |
| Bug 2: recipe token limit 4000 too high | Task 4 |
| Bug 3: vision token limit 4096 too high | Task 4 |
| Bug 4: temperature 0.7 everywhere | Task 2 |
| Bug 5: 4 vision strategies not modernised | Task 8 |
| Bug 6: rules duplicated in 3-4 files | Tasks 6, 7, 8, 9 |
| 5.1 Static/dynamic prompt split | Tasks 7, 8 |
| 5.2 Explicit context caching | Tasks 11, 12 |
| 5.3 Rule consolidation | Tasks 6, 9 |
| 5.4 Vision strategy modernisation | Task 8 |
| 5.5 Temperature calibration | Task 2 |
| 5.6 Output token limits | Task 4 |
| 5.7 Thinking budget routing fix | Task 3 |
| 5.8 Remove Mistral + Kimi | Task 5 |
| 5.9 PostHog LLM Analytics | Task 10 |
| 5.10 Scale quota increase | No code — operational note only |
| Collapse RECIPE_PRIMARY/SECONDARY | Task 1 |

All spec requirements covered. ✓
