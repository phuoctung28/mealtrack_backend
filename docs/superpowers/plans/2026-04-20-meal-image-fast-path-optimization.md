# Meal Image Fast-Path Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `/v1/meals/image` latency to p95 <= 6s by implementing concrete runtime optimizations first, then schema hardening with Pydantic.

**Architecture:** Keep the endpoint synchronous, but make the critical path bounded and deterministic: upload/persist -> vision call with strict budget -> parse/validate -> final persist/return. Remove non-essential work (translation) from the latency-critical path and add strict retry/timeout behavior. In phase 2, replace permissive dict parsing with Pydantic models for stable parse behavior.

**Tech Stack:** FastAPI, Python 3.11, Pydantic v2, LangChain Gemini adapter, pytest (unit + integration)

---

## File structure map (before tasks)

### Existing files to modify
- `src/infra/config/settings.py` — add feature flags and AI budget settings for meal analyze fast-path.
- `src/infra/adapters/vision_ai_service.py` — apply low-latency call profile (timeouts/token budget/deterministic settings).
- `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py` — fast-path execution policy + translation off critical path.
- `src/domain/strategies/meal_analysis_strategy.py` — compress basic/user-context scan prompts for smaller outputs.
- `src/domain/parsers/gpt_response_parser.py` — switch to typed schema validation in phase 2.

### New files to create
- `src/domain/services/meal_analysis/fast_path_policy.py` — single source of truth for timeout/retry/token settings used by handler and adapter.
- `src/domain/parsers/vision_response_models.py` — Pydantic models for expected vision response shape.
- `tests/unit/domain/services/meal_analysis/test_fast_path_policy.py` — policy defaults and override behavior.
- `tests/unit/domain/parsers/test_vision_response_models.py` — schema validation tests.
- `tests/unit/infra/adapters/test_vision_ai_service_fast_path.py` — ensures low-latency profile is passed into model invocation.
- `tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py` — handler behavior tests (retry cap, translation off critical path).

### Existing tests to extend
- `tests/unit/handlers/command_handlers/test_upload_uow_consolidation.py`
- `tests/integration/api/test_meals_api.py`

---

### Task 1: Add fast-path policy and config wiring

**Files:**
- Create: `src/domain/services/meal_analysis/fast_path_policy.py`
- Modify: `src/infra/config/settings.py`
- Test: `tests/unit/domain/services/meal_analysis/test_fast_path_policy.py`

- [ ] **Step 1: Write the failing test**

```python
from src.domain.services.meal_analysis.fast_path_policy import MealAnalyzeFastPathPolicy


def test_default_policy_values():
    policy = MealAnalyzeFastPathPolicy.from_settings(None)
    assert policy.primary_timeout_seconds == 2.5
    assert policy.retry_timeout_seconds == 1.5
    assert policy.max_attempts == 2
    assert policy.translation_in_critical_path is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/services/meal_analysis/test_fast_path_policy.py::test_default_policy_values -v`  
Expected: FAIL with `ModuleNotFoundError` for `fast_path_policy`.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MealAnalyzeFastPathPolicy:
    primary_timeout_seconds: float
    retry_timeout_seconds: float
    max_attempts: int
    max_output_tokens: int
    translation_in_critical_path: bool

    @classmethod
    def from_settings(cls, settings: Any | None) -> "MealAnalyzeFastPathPolicy":
        if settings is None:
            return cls(2.5, 1.5, 2, 700, False)
        return cls(
            settings.MEAL_ANALYZE_PRIMARY_TIMEOUT_SECONDS,
            settings.MEAL_ANALYZE_RETRY_TIMEOUT_SECONDS,
            settings.MEAL_ANALYZE_MAX_ATTEMPTS,
            settings.MEAL_ANALYZE_MAX_OUTPUT_TOKENS,
            settings.MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH,
        )
```

- [ ] **Step 4: Add settings fields**

```python
# in Settings class
MEAL_ANALYZE_PRIMARY_TIMEOUT_SECONDS: float = Field(default=2.5)
MEAL_ANALYZE_RETRY_TIMEOUT_SECONDS: float = Field(default=1.5)
MEAL_ANALYZE_MAX_ATTEMPTS: int = Field(default=2)
MEAL_ANALYZE_MAX_OUTPUT_TOKENS: int = Field(default=700)
MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH: bool = Field(default=False)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/domain/services/meal_analysis/test_fast_path_policy.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/domain/services/meal_analysis/fast_path_policy.py src/infra/config/settings.py tests/unit/domain/services/meal_analysis/test_fast_path_policy.py
git commit -m "feat(meal-analyze): add fast-path policy and config settings"
```

---

### Task 2: Enforce handler fast-path behavior (retry cap + translation off critical path)

**Files:**
- Modify: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Test: `tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler import UploadMealImageImmediatelyHandler
from src.app.commands.meal.upload_meal_image_immediately_command import UploadMealImageImmediatelyCommand


@pytest.mark.asyncio
async def test_translation_not_called_when_policy_disables_critical_path():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    meal = MagicMock()
    meal.meal_id = "meal-1"
    uow.meals.save = AsyncMock(return_value=meal)
    uow.meals.find_by_id = AsyncMock(return_value=meal)
    uow.commit = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(uow=uow, event_bus=MagicMock())
    handler._fast_path_policy = MagicMock(translation_in_critical_path=False, max_attempts=2)
    handler.image_store = MagicMock(save=MagicMock(return_value="mock://images/i1"))
    handler.vision_service = MagicMock(analyze=MagicMock(return_value={"structured_data": {"foods": [{"name": "rice", "quantity": 100, "unit": "g", "macros": {"protein": 2, "carbs": 25, "fat": 0}}], "dish_name": "rice", "confidence": 0.9}}))
    handler.gpt_parser = MagicMock()
    handler.gpt_parser.parse_to_nutrition.return_value = MagicMock(food_items=[MagicMock()], calories=120)
    handler.gpt_parser.parse_dish_name.return_value = "rice"
    handler.gpt_parser.parse_emoji.return_value = "🍚"
    handler.gpt_parser.extract_raw_json.return_value = "{}"
    handler.meal_translation_service = AsyncMock()

    cmd = UploadMealImageImmediatelyCommand(user_id="u1", file_contents=b"x", content_type="image/jpeg", language="vi")
    await handler.handle(cmd)
    handler.meal_translation_service.translate_meal.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py::test_translation_not_called_when_policy_disables_critical_path -v`  
Expected: FAIL because translation is currently still called for non-English requests.

- [ ] **Step 3: Implement fast-path behavior**

```python
# near translation block
should_translate_now = (
    command.language
    and command.language != "en"
    and self.meal_translation_service
    and self._fast_path_policy.translation_in_critical_path
)

if should_translate_now:
    ...
```

- [ ] **Step 4: Add bounded vision retry helper**

```python
def _run_vision_with_retry(self, command, saved_meal_id: str):
    attempts = self._fast_path_policy.max_attempts
    for attempt in range(1, attempts + 1):
        try:
            return self.vision_service.analyze(command.file_contents)
        except Exception:
            if attempt == attempts:
                raise
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py tests/unit/handlers/command_handlers/test_upload_uow_consolidation.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py
git commit -m "feat(meal-analyze): enforce fast-path retry and translation policy"
```

---

### Task 3: Shrink scan prompt and output shape for faster responses

**Files:**
- Modify: `src/domain/strategies/meal_analysis_strategy.py`
- Test: `tests/unit/domain/services/prompts/test_prompt_constants.py` (extend)  
- Test: `tests/unit/domain/test_ingredient_identification_strategy.py` (extend if needed)

- [ ] **Step 1: Write failing prompt-shape test**

```python
from src.domain.strategies.meal_analysis_strategy import BasicAnalysisStrategy


def test_basic_analysis_prompt_requires_json_only_and_compact_fields():
    prompt = BasicAnalysisStrategy().get_analysis_prompt()
    assert "Return ONLY valid JSON" in prompt
    assert "foods" in prompt
    assert "max 8 food items" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/services/prompts/test_prompt_constants.py::test_basic_analysis_prompt_requires_json_only_and_compact_fields -v`  
Expected: FAIL due to missing compact output constraints.

- [ ] **Step 3: Implement compact prompt constraints**

```python
# in BasicAnalysisStrategy.get_analysis_prompt()
# add explicit constraints:
# - Return ONLY valid JSON
# - max 8 food items
# - concise dish_name
# - no commentary text
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/domain/services/prompts/test_prompt_constants.py tests/unit/domain/test_ingredient_identification_strategy.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domain/strategies/meal_analysis_strategy.py tests/unit/domain/services/prompts/test_prompt_constants.py
git commit -m "perf(prompt): compress meal analysis prompt and output constraints"
```

---

### Task 4: Add Pydantic schema validation for vision response (phase 2)

**Files:**
- Create: `src/domain/parsers/vision_response_models.py`
- Modify: `src/domain/parsers/gpt_response_parser.py`
- Test: `tests/unit/domain/parsers/test_vision_response_models.py`

- [ ] **Step 1: Write failing schema test**

```python
import pytest
from pydantic import ValidationError
from src.domain.parsers.vision_response_models import VisionAnalyzeResponse


def test_invalid_food_item_missing_macros_raises():
    payload = {"dish_name": "rice", "foods": [{"name": "rice", "quantity": 100, "unit": "g"}], "confidence": 0.9}
    with pytest.raises(ValidationError):
        VisionAnalyzeResponse.model_validate(payload)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/parsers/test_vision_response_models.py::test_invalid_food_item_missing_macros_raises -v`  
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement models**

```python
from pydantic import BaseModel, Field, conlist


class MacrosResponse(BaseModel):
    protein: float = Field(ge=0)
    carbs: float = Field(ge=0)
    fat: float = Field(ge=0)


class FoodItemResponse(BaseModel):
    name: str
    quantity: float = Field(gt=0)
    unit: str
    macros: MacrosResponse


class VisionAnalyzeResponse(BaseModel):
    dish_name: str
    foods: conlist(FoodItemResponse, min_length=1, max_length=8)
    confidence: float = Field(ge=0, le=1)
```

- [ ] **Step 4: Wire parser to schema validation**

```python
# in GPTResponseParser.parse_to_nutrition
from src.domain.parsers.vision_response_models import VisionAnalyzeResponse

structured = gpt_response.get("structured_data")
validated = VisionAnalyzeResponse.model_validate(structured)
# continue mapping from validated model instead of raw dict
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/domain/parsers/test_vision_response_models.py tests/unit/handlers/command_handlers/test_upload_uow_consolidation.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/domain/parsers/vision_response_models.py src/domain/parsers/gpt_response_parser.py tests/unit/domain/parsers/test_vision_response_models.py
git commit -m "feat(parser): validate vision response with pydantic schemas"
```

---

### Task 5: Add regression checks for latency-sensitive behavior

**Files:**
- Modify: `tests/integration/api/test_meals_api.py`
- Modify: `tests/fixtures/mock_adapters/mock_vision_ai_service.py`

- [ ] **Step 1: Write failing integration test for non-English fast-path**

```python
def test_analyze_meal_image_non_english_still_returns_ready_fast_path(authenticated_client, sample_image_bytes):
    files = {"file": ("meal.jpg", sample_image_bytes, "image/jpeg")}
    headers = {"Accept-Language": "vi"}
    response = authenticated_client.post("/v1/meals/image/analyze", files=files, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
```

- [ ] **Step 2: Run test to verify baseline behavior**

Run: `pytest tests/integration/api/test_meals_api.py::TestMealsAPI::test_analyze_meal_image_non_english_still_returns_ready_fast_path -v`  
Expected: initially FAIL if handler still binds translation in-path; PASS after Task 2.

- [ ] **Step 3: Add deterministic mock delay control for timing assertions**

```python
class MockVisionAIService(VisionAIServicePort):
    def __init__(self, mock_response=None, artificial_delay_seconds: float = 0.0):
        self.mock_response = mock_response or self._default_response()
        self.artificial_delay_seconds = artificial_delay_seconds
```

- [ ] **Step 4: Run targeted regression suite**

Run: `pytest tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py tests/unit/domain/parsers/test_vision_response_models.py tests/integration/api/test_meals_api.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/api/test_meals_api.py tests/fixtures/mock_adapters/mock_vision_ai_service.py
git commit -m "test(meal-analyze): add latency-sensitive fast-path regressions"
```

---

## Final verification checklist (after Task 5)

- [ ] Run unit tests for touched modules:  
`pytest tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py tests/unit/domain/parsers/test_vision_response_models.py tests/unit/domain/services/meal_analysis/test_fast_path_policy.py -v`
- [ ] Run integration smoke for meals analyze route:  
`pytest tests/integration/api/test_meals_api.py -v`
- [ ] Run static checks used by repo before merge:  
`black src/ tests/ && flake8 src/ && mypy src/`

## Spec coverage self-check

1. **Concrete optimization first:** covered by Task 2 + Task 3 (retry/translation fast-path + prompt/output reduction).
2. **Hard AI budgets and deterministic behavior:** covered by Task 1 + Task 2.
3. **Pydantic in phase 2:** covered by Task 4.
4. **Regression safety:** covered by Task 5 + final verification checklist.
5. **No new investment in deprecated analyze-url:** no task touches `/analyze-url`.
