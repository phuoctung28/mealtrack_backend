# OpenAI Provider Migration Without Deleting Gemini First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move MealTrack AI generation, vision, and text embeddings from Gemini-first plumbing to OpenAI-primary routing without deleting Gemini until both production generation and embeddings are safely cut over.

**Architecture:** Keep the current 4-layer Clean Architecture boundary: API/application handlers call domain ports and infra adapters implement provider details. First collapse the vision output to one provider-neutral Pydantic contract, then introduce an injected `AIInferenceRouter` that selects provider+model routes explicitly. Gemini stays available until OpenAI routing and OpenAI embeddings have both shipped and passed canary checks.

**Tech Stack:** FastAPI, Python 3.13, Pydantic v2, SQLAlchemy 2.0, pgvector, Alembic, Redis, PyMediator, OpenAI Python SDK, Cloudflare Workers AI, Google Gemini during rollback window.

---

## Scope Check

This is a six-PR migration plan. Do not merge the PRs into one release. Each task below is independently testable and should be committed separately.

In scope:
- PR 1: canonical vision contract and retry ownership cleanup.
- PR 2: OpenAI provider and settings, with Gemini still default.
- PR 3: explicit routing, evaluation, and canary switch.
- PR 4: OpenAI embeddings with vector backfill.
- PR 5: Gemini code, dependency, and secret removal.
- PR 6: nutrition resolver accuracy work after provider migration is stable.

Out of scope:
- GPT-5.5, GPT-5.4 nano, model shopping, or multi-model optimization before OpenAI baseline is stable.
- RAG inside the image call.
- Deleting Gemini before OpenAI generation and OpenAI embeddings are both live.
- Removing Firebase or Google Cloud config that is unrelated to Gemini AI.

## Current Evidence

- Live meal scan route: `UploadMealImageImmediatelyHandler -> VisionAIService -> AIModelManager`.
- Canonical vision schema exists at `src/domain/model/ai/nutrition_contracts.py`, but `VisionNutritionResponse` currently has `extra="ignore"` and no `emoji`.
- Legacy vision schema exists at `src/domain/parsers/vision_response_models.py` and still drives parser and Gemini provider validation.
- `VisionAIService` validates canonical output, converts it back to legacy shape, and retries validation once.
- `AIModelManager` instantiates `GeminiProvider` internally and infers provider ownership from model-name prefixes.
- Gemini startup cache is wired in `src/api/main.py`.
- Gemini text embeddings are wired in `src/api/dependencies/meal_image_cache.py` and `scripts/resolve_pending_images.py`.
- `meal_image_cache.text_embedding` is `Vector(512)`, so OpenAI embeddings can use 512 dimensions but must not share the same vector column without version separation.

## OpenAI Docs Anchors

- `gpt-5.4-mini-2026-03-17` is the pinned initial model for text and vision.
- Use the Responses API and structured output parsing for provider-facing Pydantic contracts.
- Use image `detail="high"` for food images. Do not claim `original` is required for this migration.
- Use `text-embedding-3-small` with `dimensions=512` for vector length compatibility.
- Set `store=False` on Responses calls and avoid logging prompt, image, or user food text.

References:
- https://developers.openai.com/api/docs/models/gpt-5.4-mini
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/docs/guides/images-vision
- https://developers.openai.com/api/docs/guides/embeddings
- https://developers.openai.com/api/docs/guides/your-data

## File Structure

### PR 1 Files

- Modify: `src/domain/model/ai/nutrition_contracts.py` — strict canonical vision schema with `emoji`.
- Modify: `src/domain/model/ai/__init__.py` — export any moved AI contract symbols.
- Modify: `src/domain/parsers/vision_response_parser.py` — parse canonical `VisionNutritionResponse` directly.
- Delete: `src/domain/parsers/vision_response_models.py` — remove legacy `VisionAnalyzeResponse` after callers migrate.
- Modify: `src/domain/services/meal_analysis/prompt_eval_loop.py` — validate prompt eval payloads with `VisionNutritionResponse`.
- Modify: `src/infra/adapters/vision_ai_service.py` — return canonical structured data; remove validation repair retry and legacy conversion.
- Modify: `src/infra/services/ai/providers/gemini_provider.py` — use `VisionNutritionResponse` while Gemini remains enabled.
- Modify: `tests/unit/domain/model/ai/test_nutrition_contracts.py` — strict contract tests.
- Modify: `tests/unit/domain/parsers/test_gpt_response_parser.py` — canonical parser tests.
- Delete: `tests/unit/domain/parsers/test_vision_response_models.py` — legacy model tests.
- Modify: `tests/unit/domain/services/meal_analysis/test_prompt_eval_loop.py` — canonical eval payloads.
- Modify: `tests/unit/infra/adapters/test_vision_ai_service_resilience.py` — canonical response and no validation repair retry.
- Modify: `tests/unit/infra/services/ai/providers/test_gemini_provider.py` — canonical Gemini provider schema.
- Modify: `tests/unit/infra/services/ai/test_gemini_provider_gateway.py` — canonical Gemini gateway schema.
- Modify: `tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py` — canonical vision schema expectations.

### PR 2 Files

- Modify: `pyproject.toml` — add pinned `openai` dependency.
- Modify: `src/infra/config/settings.py` — add OpenAI route settings; remove stale `OPENAI_MODEL`.
- Modify: `.env.example` — document OpenAI settings.
- Create: `src/infra/services/ai/providers/openai_provider.py` — native OpenAI SDK provider.
- Create: `tests/unit/infra/services/ai/providers/test_openai_provider.py` — provider tests.

### PR 3 Files

- Create: `src/domain/model/ai/model_purpose.py` — provider-neutral purpose enum.
- Create: `src/infra/services/ai/model_route.py` — provider+model route value object.
- Create: `src/infra/services/ai/ai_inference_router.py` — injected provider router.
- Modify: `src/infra/services/ai/ai_model_manager.py` — compatibility wrapper during migration or delete after callers move.
- Modify: `src/infra/adapters/vision_ai_service.py` — depend on router.
- Modify: handlers that import `ModelPurpose` from infra.
- Create: `tests/unit/infra/services/ai/test_ai_inference_router.py` — route/fallback tests.

### PR 4 Files

- Create: `src/infra/adapters/openai_text_embedding_adapter.py` — OpenAI text embedding adapter.
- Modify: `src/api/dependencies/meal_image_cache.py` — inject OpenAI text embedder after backfill gate.
- Modify: `scripts/resolve_pending_images.py` — write OpenAI embeddings for pending-image cache.
- Modify: `src/infra/database/models/meal_image_cache.py` — add v2 vector metadata.
- Create: `alembic/versions/<timestamp>_meal_image_cache_openai_embedding_v2.py` — migration.
- Modify: cache repositories that read or write `meal_image_cache.text_embedding`.
- Create: `tests/unit/infra/adapters/test_openai_text_embedding_adapter.py`.
- Modify: `tests/unit/api/dependencies/test_meal_image_cache.py`.

### PR 5 Files

- Delete: `src/infra/services/ai/providers/gemini_provider.py`.
- Delete: `src/infra/services/ai/gemini_model_manager.py`.
- Delete: `src/infra/services/ai/gemini_model_config.py`.
- Delete: `src/infra/services/ai/gemini_cache_manager.py`.
- Delete: `src/infra/services/ai/gemini_cache_handler.py`.
- Delete: `src/infra/ai/gemini_service.py`.
- Delete: `src/infra/adapters/gemini_text_embedding_adapter.py`.
- Modify: `src/api/main.py` — remove Gemini cache startup/shutdown.
- Modify: `pyproject.toml` — remove `langchain-google-genai` and `google-genai`.
- Modify: `src/infra/config/settings.py` and `.env.example` — remove Gemini AI settings only.
- Modify: docs and tests that mention Gemini as active AI provider.

### PR 6 Files

- Create: `src/domain/model/ai/vision_food_identity_contract.py` — model output without invented macros.
- Create: `src/domain/services/nutrition_resolver.py` — deterministic nutrition resolver.
- Modify: `src/infra/adapters/food_data_service.py` usage — USDA candidate lookup.
- Modify: `src/infra/adapters/fat_secret_service.py` usage — branded/restaurant candidates.
- Modify: `src/infra/adapters/open_food_facts_service.py` usage — packaged food candidates.
- Modify: `src/infra/adapters/vision_ai_service.py` — use identity contract after resolver exists.
- Create: `tests/unit/domain/services/test_nutrition_resolver.py`.

### Task 0: Execution Preflight

**Files:**
- Read: `README.md`
- Read: `docs/codebase-summary.md`
- Read: `docs/code-standards.md`
- Read: `docs/external-services.md`

- [ ] **Step 1: Confirm branch and dirty files**

Run:

```bash
git branch --show-current
git status --short
```

Expected:

```text
delivery
```

If dirty files are unrelated to this migration, leave them untouched.

- [ ] **Step 2: Create an isolated branch before coding**

Run:

```bash
git switch -c codex/openai-provider-migration-pr1
```

Expected:

```text
Switched to a new branch 'codex/openai-provider-migration-pr1'
```

- [ ] **Step 3: Run baseline targeted tests**

Run:

```bash
uv run pytest \
  tests/unit/domain/model/ai/test_nutrition_contracts.py \
  tests/unit/domain/parsers/test_gpt_response_parser.py \
  tests/unit/infra/adapters/test_vision_ai_service_resilience.py \
  tests/unit/infra/services/ai/test_ai_vision_failure_routing.py \
  -q
```

Expected: current tests pass before edits. If they fail before edits, record the failing test names in the PR notes and fix only failures caused by this migration.

### Task 1: Canonical Vision Contract

**Files:**
- Modify: `src/domain/model/ai/nutrition_contracts.py`
- Test: `tests/unit/domain/model/ai/test_nutrition_contracts.py`

- [ ] **Step 1: Add failing strict-contract tests**

Append these tests inside `TestVisionNutritionResponse` in `tests/unit/domain/model/ai/test_nutrition_contracts.py`:

```python
    def test_accepts_optional_emoji(self):
        response = VisionNutritionResponse.model_validate(
            {
                "dish_name": "Chicken rice bowl",
                "emoji": "🍚",
                "foods": [
                    {
                        "name": "Grilled chicken",
                        "quantity_g": 150.0,
                        "macros": _valid_macros(),
                        "confidence": 0.92,
                    }
                ],
                "confidence": 0.88,
            }
        )

        assert response.emoji == "🍚"

    def test_rejects_extra_top_level_fields(self):
        with pytest.raises(ValidationError):
            VisionNutritionResponse.model_validate(
                {
                    "dish_name": "Chicken rice bowl",
                    "foods": [
                        {
                            "name": "Grilled chicken",
                            "quantity_g": 150.0,
                            "macros": _valid_macros(),
                        }
                    ],
                    "confidence": 0.88,
                    "calories": 9999,
                }
            )

    def test_rejects_extra_food_fields(self):
        with pytest.raises(ValidationError):
            VisionNutritionResponse.model_validate(
                {
                    "dish_name": "Chicken rice bowl",
                    "foods": [
                        {
                            "name": "Grilled chicken",
                            "quantity_g": 150.0,
                            "unit": "g",
                            "macros": _valid_macros(),
                        }
                    ],
                    "confidence": 0.88,
                }
            )

    def test_rejects_extra_macro_fields(self):
        macros = _valid_macros()
        macros["calories"] = 9999.0

        with pytest.raises(ValidationError):
            VisionNutritionResponse.model_validate(
                {
                    "dish_name": "Chicken rice bowl",
                    "foods": [
                        {
                            "name": "Grilled chicken",
                            "quantity_g": 150.0,
                            "macros": macros,
                        }
                    ],
                }
            )
```

- [ ] **Step 2: Run strict-contract tests and verify failure**

Run:

```bash
uv run pytest tests/unit/domain/model/ai/test_nutrition_contracts.py::TestVisionNutritionResponse -q
```

Expected: fails because `emoji` is missing and extra fields are ignored.

- [ ] **Step 3: Make provider-facing vision models strict**

In `src/domain/model/ai/nutrition_contracts.py`, change only the provider-facing image models:

```python
class AINutritionMacros(BaseModel):
    """Macronutrients reported by AI, in grams."""

    model_config = ConfigDict(extra="forbid")
```

```python
class VisionFoodEstimate(BaseModel):
    """Single food estimate extracted from an image."""

    model_config = ConfigDict(extra="forbid")
```

```python
class BeverageMetadata(BaseModel):
    """Metadata for packaged beverage images detected by AI."""

    model_config = ConfigDict(extra="forbid")
```

```python
class VisionNutritionResponse(BaseModel):
    """Structured image meal-analysis response."""

    model_config = ConfigDict(extra="forbid")

    is_food: bool = Field(True, description="Whether the image contains edible food")
    dish_name: str | None = Field(None, max_length=200)
    emoji: str | None = Field(None, max_length=32)
    foods: list[VisionFoodEstimate] = Field(
        default_factory=list,
        max_length=MAX_AI_FOOD_ITEMS,
        description="Foods visible in the image",
    )
    confidence: float = Field(0.5, ge=0, le=1)
    beverage_metadata: BeverageMetadata | None = None
```

Do not change `MealTextFoodEstimate` or `MealTextNutritionResponse` in this task.

- [ ] **Step 4: Update the old calorie-ignore assertion**

Replace the old assertion in `test_accepts_realistic_food_quantities`:

```python
        assert "calories" not in response.model_dump()
```

with this assertion:

```python
        assert response.emoji is None
```

Remove `"calories": 9999` from that test payload.

- [ ] **Step 5: Run contract tests**

Run:

```bash
uv run pytest tests/unit/domain/model/ai/test_nutrition_contracts.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit PR 1 contract change**

Run:

```bash
git add src/domain/model/ai/nutrition_contracts.py tests/unit/domain/model/ai/test_nutrition_contracts.py
git commit -m "refactor: enforce canonical vision nutrition contract"
```

Expected: commit succeeds.

### Task 2: Canonical Vision Parser

**Files:**
- Modify: `src/domain/parsers/vision_response_parser.py`
- Delete after caller migration: `src/domain/parsers/vision_response_models.py`
- Modify: `src/domain/services/meal_analysis/prompt_eval_loop.py`
- Test: `tests/unit/domain/parsers/test_gpt_response_parser.py`
- Delete after caller migration: `tests/unit/domain/parsers/test_vision_response_models.py`
- Test: `tests/unit/domain/services/meal_analysis/test_prompt_eval_loop.py`

- [ ] **Step 1: Add canonical parser tests**

In `tests/unit/domain/parsers/test_gpt_response_parser.py`, add these tests:

```python
def test_parse_to_nutrition_accepts_canonical_quantity_g(gpt_parser):
    gpt_response = {
        "structured_data": {
            "is_food": True,
            "dish_name": "Chicken rice bowl",
            "emoji": "🍚",
            "foods": [
                {
                    "name": "Grilled chicken",
                    "quantity_g": 150.0,
                    "macros": {
                        "protein_g": 35.0,
                        "carbs_g": 0.0,
                        "fat_g": 5.0,
                        "fiber_g": 0.0,
                        "sugar_g": 0.0,
                    },
                    "confidence": 0.92,
                }
            ],
            "confidence": 0.88,
        }
    }

    nutrition = gpt_parser.parse_to_nutrition(gpt_response)

    assert nutrition.food_items[0].quantity == 150.0
    assert nutrition.food_items[0].unit == "g"
    assert nutrition.food_items[0].macros.protein == 35.0
    assert nutrition.confidence_score == 0.88


def test_parse_to_nutrition_rejects_legacy_quantity_unit_shape(gpt_parser):
    gpt_response = {
        "structured_data": {
            "is_food": True,
            "dish_name": "Chicken rice bowl",
            "foods": [
                {
                    "name": "Grilled chicken",
                    "quantity": 150.0,
                    "unit": "g",
                    "macros": {
                        "protein": 35.0,
                        "carbs": 0.0,
                        "fat": 5.0,
                    },
                }
            ],
            "confidence": 0.88,
        }
    }

    with pytest.raises(GPTResponseParsingError):
        gpt_parser.parse_to_nutrition(gpt_response)


def test_parse_emoji_reads_canonical_emoji(gpt_parser):
    gpt_response = {
        "structured_data": {
            "is_food": True,
            "dish_name": "Chicken rice bowl",
            "emoji": "🍚",
            "foods": [
                {
                    "name": "Grilled chicken",
                    "quantity_g": 150.0,
                    "macros": {
                        "protein_g": 35.0,
                        "carbs_g": 0.0,
                        "fat_g": 5.0,
                    },
                }
            ],
        }
    }

    assert gpt_parser.parse_emoji(gpt_response) == "🍚"
```

- [ ] **Step 2: Run parser tests and verify failure**

Run:

```bash
uv run pytest tests/unit/domain/parsers/test_gpt_response_parser.py -q
```

Expected: new canonical tests fail because parser still validates `VisionAnalyzeResponse` and requires `quantity` plus `unit`.

- [ ] **Step 3: Replace parser validation with canonical contract**

In `src/domain/parsers/vision_response_parser.py`, replace:

```python
from pydantic import ValidationError
from src.domain.parsers.vision_response_models import VisionAnalyzeResponse
```

with:

```python
from pydantic import ValidationError
from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
```

Replace the strict validation and normalized dict block in `parse_to_nutrition()` with:

```python
            normalized_data = self._normalize_structured_data(data)
            canonical = VisionNutritionResponse.model_validate(normalized_data)

            food_items = self._parse_food_items(canonical)
            total_macros = self._calculate_total_macros(food_items)
            confidence_score = min(max(0.0, float(canonical.confidence)), 1.0)
```

Replace `_parse_food_items()` with:

```python
    def _parse_food_items(self, data: VisionNutritionResponse) -> list[FoodItem]:
        """Parse food items from canonical AI vision output."""
        food_items: list[FoodItem] = []

        for food_data in data.foods[: self.MAX_FOOD_ITEMS]:
            macros = Macros(
                protein=float(food_data.macros.protein_g),
                carbs=float(food_data.macros.carbs_g),
                fat=float(food_data.macros.fat_g),
                fiber=float(food_data.macros.fiber_g),
                sugar=float(food_data.macros.sugar_g),
            )

            food_items.append(
                FoodItem(
                    id=str(uuid.uuid4()),
                    name=food_data.name,
                    quantity=float(food_data.quantity_g),
                    unit="g",
                    macros=macros,
                    micros=None,
                    confidence=min(max(0.0, float(food_data.confidence)), 1.0),
                )
            )

        return food_items
```

Replace `_calculate_total_macros()` with:

```python
    def _calculate_total_macros(self, food_items: list[FoodItem]) -> Macros:
        """Calculate total macros from canonical food items."""
        return Macros(
            protein=sum(item.macros.protein for item in food_items),
            carbs=sum(item.macros.carbs for item in food_items),
            fat=sum(item.macros.fat for item in food_items),
            fiber=sum(item.macros.fiber for item in food_items),
            sugar=sum(item.macros.sugar for item in food_items),
        )
```

- [ ] **Step 4: Keep food guard and metadata readers stable**

Do not change `parse_is_food()`, `parse_dish_name()`, `parse_emoji()`, or `extract_raw_json()` except for import fallout. Handlers depend on these methods.

- [ ] **Step 5: Update prompt eval validation**

In `src/domain/services/meal_analysis/prompt_eval_loop.py`, replace:

```python
from src.domain.parsers.vision_response_models import VisionAnalyzeResponse
```

with:

```python
from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
```

Replace:

```python
                    VisionAnalyzeResponse.model_validate(structured)
```

with:

```python
                    VisionNutritionResponse.model_validate(structured)
```

- [ ] **Step 6: Run parser and eval tests**

Run:

```bash
uv run pytest \
  tests/unit/domain/parsers/test_gpt_response_parser.py \
  tests/unit/domain/services/meal_analysis/test_prompt_eval_loop.py \
  -q
```

Expected: parser tests pass after updating old legacy fixture payloads to canonical `quantity_g` and macro `_g` keys.

- [ ] **Step 7: Commit parser migration**

Run:

```bash
git add \
  src/domain/parsers/vision_response_parser.py \
  src/domain/services/meal_analysis/prompt_eval_loop.py \
  tests/unit/domain/parsers/test_gpt_response_parser.py \
  tests/unit/domain/services/meal_analysis/test_prompt_eval_loop.py
git commit -m "refactor: parse canonical vision nutrition output"
```

Expected: commit succeeds.

### Task 3: Vision Service Returns Canonical Data Once

**Files:**
- Modify: `src/infra/adapters/vision_ai_service.py`
- Test: `tests/unit/infra/adapters/test_vision_ai_service_resilience.py`

- [ ] **Step 1: Add failing no-retry and canonical-return tests**

In `tests/unit/infra/adapters/test_vision_ai_service_resilience.py`, replace legacy assertions that expect `quantity` and `unit` with canonical assertions:

```python
    assert result["structured_data"]["foods"][0]["quantity_g"] == 180
    assert "unit" not in result["structured_data"]["foods"][0]
```

Replace `test_analyze_with_strategy_retries_invalid_structured_output_once` with:

```python
@pytest.mark.asyncio
async def test_analyze_with_strategy_does_not_retry_invalid_structured_output(
    service, mock_ai_manager, mock_strategy
):
    invalid = {
        "dish_name": "Rice bowl",
        "foods": [
            {
                "name": "rice",
                "quantity_g": 150000,
                "macros": {"protein_g": 4, "carbs_g": 50, "fat_g": 1},
            }
        ],
    }
    mock_ai_manager.generate_with_vision = AsyncMock(return_value=invalid)

    with pytest.raises(AIOutputValidationError) as exc_info:
        await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert mock_ai_manager.generate_with_vision.await_count == 1
    assert exc_info.value.purpose == "meal_scan"
    assert exc_info.value.attempt_count == 1
    assert "foods.0.quantity_g" in exc_info.value.validation_details[0]
```

Replace `test_analyze_with_strategy_raises_controlled_error_after_retry_failure` with:

```python
@pytest.mark.asyncio
async def test_analyze_with_strategy_raises_controlled_error_without_repair_retry(
    service, mock_ai_manager, mock_strategy
):
    invalid = {
        "dish_name": "Rice bowl",
        "foods": [
            {
                "name": "rice",
                "quantity_g": 150000,
                "macros": {"protein_g": 4, "carbs_g": 50, "fat_g": 1},
            }
        ],
    }
    mock_ai_manager.generate_with_vision = AsyncMock(return_value=invalid)

    with pytest.raises(AIOutputValidationError) as exc_info:
        await service.analyze_with_strategy(b"fake_image", mock_strategy)

    assert mock_ai_manager.generate_with_vision.await_count == 1
    assert exc_info.value.attempt_count == 1
```

- [ ] **Step 2: Run vision service tests and verify failure**

Run:

```bash
uv run pytest tests/unit/infra/adapters/test_vision_ai_service_resilience.py -q
```

Expected: fails because service still returns legacy payload and retries validation once.

- [ ] **Step 3: Remove validation repair retry from imports and constants**

In `src/infra/adapters/vision_ai_service.py`, replace:

```python
from src.domain.services.ai_output_validation_service import (
    build_validation_retry_prompt,
    validate_ai_output,
)
```

with:

```python
from src.domain.services.ai_output_validation_service import validate_ai_output
```

Remove:

```python
MAX_VALIDATION_ATTEMPTS = 2
```

- [ ] **Step 4: Replace retry loop with a single validated call**

Replace the block that starts with `for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):` in `analyze_with_strategy()` with:

```python
        try:
            result = await self._ai_manager.generate_with_vision(
                purpose=ModelPurpose.MEAL_SCAN,
                prompt=base_prompt,
                image_data=image_bytes,
                system_message=strategy.get_analysis_prompt(),
                max_tokens=self._max_output_tokens,
            )
            structured_data = validate_ai_output(
                result,
                schema=VisionNutritionResponse,
                purpose=VISION_VALIDATION_PURPOSE,
                attempt_count=1,
            )
            return {
                "raw_response": json.dumps(structured_data),
                "structured_data": structured_data,
                "strategy_used": strategy.get_strategy_name(),
            }
        except AIOutputValidationError:
            raise
        except AIUnavailableError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to analyze image with {strategy.get_strategy_name()}: {str(e)}"
            ) from e
```

Delete `_to_legacy_vision_payload()`.

- [ ] **Step 5: Run vision service tests**

Run:

```bash
uv run pytest tests/unit/infra/adapters/test_vision_ai_service_resilience.py -q
```

Expected: tests pass after fixture payloads use canonical macro keys.

- [ ] **Step 6: Commit vision service migration**

Run:

```bash
git add src/infra/adapters/vision_ai_service.py tests/unit/infra/adapters/test_vision_ai_service_resilience.py
git commit -m "refactor: return canonical vision analysis payloads"
```

Expected: commit succeeds.

### Task 4: Migrate Existing Providers to the Canonical Contract

**Files:**
- Modify: `src/infra/services/ai/providers/gemini_provider.py`
- Modify: `src/infra/services/ai/providers/cloudflare_workers_ai_provider.py`
- Test: `tests/unit/infra/services/ai/providers/test_gemini_provider.py`
- Test: `tests/unit/infra/services/ai/test_gemini_provider_gateway.py`
- Test: `tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py`

- [ ] **Step 1: Add provider contract tests**

In Gemini provider tests, assert the provider imports and validates `VisionNutritionResponse` rather than `VisionAnalyzeResponse`. Use this fixture shape:

```python
canonical_payload = {
    "is_food": True,
    "dish_name": "Bowl",
    "emoji": "🥣",
    "foods": [
        {
            "name": "rice",
            "quantity_g": 180.0,
            "macros": {
                "protein_g": 4.0,
                "carbs_g": 50.0,
                "fat_g": 1.0,
            },
            "confidence": 0.9,
        }
    ],
    "confidence": 0.9,
}
```

- [ ] **Step 2: Run provider tests and verify failure**

Run:

```bash
uv run pytest \
  tests/unit/infra/services/ai/providers/test_gemini_provider.py \
  tests/unit/infra/services/ai/test_gemini_provider_gateway.py \
  tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py \
  -q
```

Expected: fails where tests or provider code still reference `VisionAnalyzeResponse`.

- [ ] **Step 3: Update Gemini gateway schema**

In `src/infra/services/ai/providers/gemini_provider.py`, replace both imports of `VisionAnalyzeResponse` with:

```python
from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
```

In `_generate_vision_via_gateway()`, replace:

```python
            response_schema=VisionAnalyzeResponse,
```

with:

```python
            response_schema=VisionNutritionResponse,
```

Replace the parsed-response validation block with:

```python
        if response.parsed is not None:
            if hasattr(response.parsed, "model_dump"):
                return response.parsed.model_dump()
            return VisionNutritionResponse.model_validate(response.parsed).model_dump()
```

Replace the text fallback validation with:

```python
        parsed = self._extract_json(text)
        validated = VisionNutritionResponse.model_validate(parsed)
        return validated.model_dump()
```

- [ ] **Step 4: Update Gemini LangChain structured schema**

In `generate_with_vision()`, replace:

```python
                VisionAnalyzeResponse.model_json_schema(),
```

with:

```python
                VisionNutritionResponse.model_json_schema(),
```

- [ ] **Step 5: Validate Cloudflare vision output when schema is provided**

In `src/infra/services/ai/providers/cloudflare_workers_ai_provider.py`, after `parsed = extract_ai_json(text)`, add schema validation support:

```python
        schema = kwargs.get("schema")
        if schema is not None:
            try:
                return schema.model_validate(parsed).model_dump()
            except ValidationError as exc:
                raise AIVisionError(
                    f"[CF-WORKERS-AI-VISION-SCHEMA-FAIL] provider=cloudflare-workers-ai model={model}",
                    kind=AIVisionFailureKind.schema_validation,
                    provider="cloudflare-workers-ai",
                    model=model,
                ) from exc
```

Then return `parsed` as before.

- [ ] **Step 6: Pass canonical schema from the manager**

In `src/infra/services/ai/ai_model_manager.py`, inside `generate_with_vision()`, pass the schema through to providers:

```python
                    schema=kwargs.get("schema"),
```

The full provider call should include this keyword before `**kwargs`.

- [ ] **Step 7: Pass canonical schema from VisionAIService**

In `src/infra/adapters/vision_ai_service.py`, add this keyword to the `generate_with_vision()` call:

```python
                schema=VisionNutritionResponse,
```

- [ ] **Step 8: Run provider tests**

Run:

```bash
uv run pytest \
  tests/unit/infra/services/ai/providers/test_gemini_provider.py \
  tests/unit/infra/services/ai/test_gemini_provider_gateway.py \
  tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py \
  tests/unit/infra/services/ai/test_ai_vision_failure_routing.py \
  -q
```

Expected: all selected tests pass.

- [ ] **Step 9: Remove legacy model file after grep is clean**

Run:

```bash
rg "VisionAnalyzeResponse|vision_response_models" src tests
```

Expected: no remaining source imports except files being deleted. Then run:

```bash
git rm src/domain/parsers/vision_response_models.py tests/unit/domain/parsers/test_vision_response_models.py
```

- [ ] **Step 10: Commit provider migration**

Run:

```bash
git add \
  src/infra/services/ai/providers/gemini_provider.py \
  src/infra/services/ai/providers/cloudflare_workers_ai_provider.py \
  src/infra/services/ai/ai_model_manager.py \
  src/infra/adapters/vision_ai_service.py \
  tests/unit/infra/services/ai/providers/test_gemini_provider.py \
  tests/unit/infra/services/ai/test_gemini_provider_gateway.py \
  tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py
git add -u src/domain/parsers tests/unit/domain/parsers
git commit -m "refactor: migrate vision providers to canonical schema"
```

Expected: commit succeeds.

### Task 5: Finish PR 1 Regression Gate

**Files:**
- Read: all files changed in Tasks 1 through 4.

- [ ] **Step 1: Run PR 1 focused test suite**

Run:

```bash
uv run pytest \
  tests/unit/domain/model/ai/test_nutrition_contracts.py \
  tests/unit/domain/parsers/test_gpt_response_parser.py \
  tests/unit/domain/services/meal_analysis/test_prompt_eval_loop.py \
  tests/unit/infra/adapters/test_vision_ai_service_resilience.py \
  tests/unit/infra/services/ai/providers/test_gemini_provider.py \
  tests/unit/infra/services/ai/test_gemini_provider_gateway.py \
  tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py \
  tests/unit/infra/services/ai/test_ai_vision_failure_routing.py \
  -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run compile and architecture checks**

Run:

```bash
uv run python -m compileall -q src tests
uv run lint-imports
```

Expected: both commands exit 0.

- [ ] **Step 3: Search for legacy contract names**

Run:

```bash
rg "VisionAnalyzeResponse|vision_response_models|_to_legacy_vision_payload|MAX_VALIDATION_ATTEMPTS" src tests
```

Expected: no matches for `VisionAnalyzeResponse`, `vision_response_models`, or `_to_legacy_vision_payload`. `MAX_VALIDATION_ATTEMPTS` may still exist in text-parse code; it must not exist in `src/infra/adapters/vision_ai_service.py`.

- [ ] **Step 4: Commit final PR 1 cleanup**

Run:

```bash
git status --short
git add src tests
git commit -m "test: lock canonical vision contract regression coverage"
```

Expected: commit succeeds if Step 3 produced cleanup changes. If there are no changes, skip this commit.

### Task 6: Add OpenAI Provider With Gemini Still Default

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/infra/config/settings.py`
- Modify: `.env.example`
- Create: `src/infra/services/ai/providers/openai_provider.py`
- Test: `tests/unit/infra/services/ai/providers/test_openai_provider.py`

- [ ] **Step 1: Add failing provider tests**

Create `tests/unit/infra/services/ai/providers/test_openai_provider.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
from src.domain.ports.ai_provider_port import AICapability
from src.infra.services.ai.providers.openai_provider import OpenAIProvider


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


def test_openai_provider_capabilities():
    provider = OpenAIProvider(
        api_key="test-key",
        request_timeout_seconds=20,
        max_retries=1,
        store_responses=False,
    )

    assert provider.provider_name == "openai"
    assert AICapability.TEXT_GENERATION in provider.supported_capabilities
    assert AICapability.VISION in provider.supported_capabilities
    assert AICapability.STRUCTURED_OUTPUT in provider.supported_capabilities


@pytest.mark.asyncio
async def test_generate_with_vision_uses_responses_parse_and_store_false():
    provider = OpenAIProvider(
        api_key="test-key",
        request_timeout_seconds=20,
        max_retries=1,
        store_responses=False,
    )
    parsed = _parsed_vision_response()
    provider._client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(output_parsed=parsed)
    )

    result = await provider.generate_with_vision(
        model="gpt-5.4-mini-2026-03-17",
        prompt="Identify food.",
        image_data=b"image-bytes",
        system_message="Return canonical JSON.",
        schema=VisionNutritionResponse,
        image_mime_type="image/png",
        max_tokens=1500,
    )

    assert result["emoji"] == "🍚"
    call_kwargs = provider._client.responses.parse.await_args.kwargs
    assert call_kwargs["model"] == "gpt-5.4-mini-2026-03-17"
    assert call_kwargs["store"] is False
    assert call_kwargs["text_format"] is VisionNutritionResponse
    user_content = call_kwargs["input"][1]["content"]
    assert user_content[1]["image_url"].startswith("data:image/png;base64,")
    assert user_content[1]["detail"] == "high"
```

- [ ] **Step 2: Run provider tests and verify import failure**

Run:

```bash
uv run pytest tests/unit/infra/services/ai/providers/test_openai_provider.py -q
```

Expected: fails because `openai_provider.py` does not exist.

- [ ] **Step 3: Add OpenAI dependency**

In `pyproject.toml`, add this dependency near `httpx`:

```toml
    "openai>=2.14.0,<3.0.0",
```

Run:

```bash
uv sync
```

Expected: dependency resolution succeeds.

- [ ] **Step 4: Add OpenAI settings**

In `src/infra/config/settings.py`, replace stale `LLM_PROVIDER` and `OPENAI_MODEL` fields with:

```python
    AI_PRIMARY_PROVIDER: str = Field(
        default="gemini",
        description="Primary AI provider. Use 'openai' only after canary approval.",
    )
    AI_FALLBACK_PROVIDER: str = Field(
        default="cloudflare-workers-ai",
        description="Fallback AI provider after the primary provider fails transiently.",
    )
    OPENAI_API_KEY: str | None = Field(default=None)
    OPENAI_VISION_MODEL: str = Field(default="gpt-5.4-mini-2026-03-17")
    OPENAI_TEXT_MODEL: str = Field(default="gpt-5.4-mini-2026-03-17")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    OPENAI_EMBEDDING_DIMENSIONS: int = Field(default=512)
    OPENAI_REQUEST_TIMEOUT_SECONDS: int = Field(default=20)
    OPENAI_MAX_RETRIES: int = Field(default=1)
    OPENAI_STORE_RESPONSES: bool = Field(default=False)
```

Keep existing Gemini settings in this PR.

- [ ] **Step 5: Create OpenAI provider**

Create `src/infra/services/ai/providers/openai_provider.py`:

```python
"""OpenAI implementation of AIProviderPort using the native Responses API."""

from __future__ import annotations

import base64
import re
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

from src.domain.ports.ai_provider_port import AICapability, AIProviderPort


class OpenAIProvider(AIProviderPort):
    """OpenAI provider for text, vision, and structured output."""

    def __init__(
        self,
        *,
        api_key: str,
        request_timeout_seconds: int,
        max_retries: int,
        store_responses: bool,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=request_timeout_seconds,
            max_retries=max_retries,
        )
        self._store_responses = store_responses

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supported_capabilities(self) -> set[AICapability]:
        return {
            AICapability.TEXT_GENERATION,
            AICapability.VISION,
            AICapability.STRUCTURED_OUTPUT,
        }

    def get_available_models(self) -> list[str]:
        return []

    async def generate(
        self,
        model: str,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int | None = None,
        schema: type | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if schema is not None:
            response = await self._client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                text_format=schema,
                max_output_tokens=max_tokens,
                reasoning={"effort": "none"},
                store=self._store_responses,
            )
            parsed = response.output_parsed
            if hasattr(parsed, "model_dump"):
                return parsed.model_dump()
            return dict(parsed)

        response = await self._client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            max_output_tokens=max_tokens,
            reasoning={"effort": "none"},
            store=self._store_responses,
        )
        return {"raw_content": response.output_text}

    async def generate_with_vision(
        self,
        model: str,
        prompt: str,
        image_data: bytes,
        system_message: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        schema = kwargs["schema"]
        max_tokens: int | None = kwargs.get("max_tokens")
        image_mime_type = kwargs.get("image_mime_type", "image/jpeg")
        image_b64 = base64.b64encode(image_data).decode("ascii")
        image_data_url = f"data:{image_mime_type};base64,{image_b64}"

        response = await self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_message or ""},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                            "detail": "high",
                        },
                    ],
                },
            ],
            text_format=schema,
            max_output_tokens=max_tokens,
            reasoning={"effort": "none"},
            store=self._store_responses,
        )
        parsed = response.output_parsed
        if hasattr(parsed, "model_dump"):
            return parsed.model_dump()
        return dict(parsed)

    def extract_error_code(self, error: Exception) -> int | str | None:
        if isinstance(error, RateLimitError):
            return 429
        if isinstance(error, APITimeoutError):
            return "timeout"
        if isinstance(error, APIConnectionError):
            return "connection"
        if isinstance(error, APIStatusError):
            return error.status_code

        match = re.search(r"\b(429|500|502|503|504)\b", str(error))
        if match:
            return int(match.group(1))
        return None
```

- [ ] **Step 6: Add env example keys**

In `.env.example`, add:

```env
AI_PRIMARY_PROVIDER=gemini
AI_FALLBACK_PROVIDER=cloudflare-workers-ai
OPENAI_API_KEY=
OPENAI_VISION_MODEL=gpt-5.4-mini-2026-03-17
OPENAI_TEXT_MODEL=gpt-5.4-mini-2026-03-17
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=512
OPENAI_REQUEST_TIMEOUT_SECONDS=20
OPENAI_MAX_RETRIES=1
OPENAI_STORE_RESPONSES=false
```

- [ ] **Step 7: Run OpenAI provider tests**

Run:

```bash
uv run pytest tests/unit/infra/services/ai/providers/test_openai_provider.py -q
```

Expected: tests pass.

- [ ] **Step 8: Commit OpenAI provider**

Run:

```bash
git add pyproject.toml uv.lock .env.example src/infra/config/settings.py src/infra/services/ai/providers/openai_provider.py tests/unit/infra/services/ai/providers/test_openai_provider.py
git commit -m "feat: add openai ai provider"
```

Expected: commit succeeds.

### Task 7: Explicit AI Routing and Canary Switch

**Files:**
- Create: `src/domain/model/ai/model_purpose.py`
- Create: `src/infra/services/ai/model_route.py`
- Create: `src/infra/services/ai/ai_inference_router.py`
- Modify: `src/infra/services/ai/ai_model_manager.py`
- Modify: `src/infra/adapters/vision_ai_service.py`
- Modify: handlers importing `ModelPurpose`
- Test: `tests/unit/infra/services/ai/test_ai_inference_router.py`

- [ ] **Step 1: Add router tests**

Create `tests/unit/infra/services/ai/test_ai_inference_router.py`:

```python
from unittest.mock import AsyncMock

import pytest

from src.domain.model.ai.model_purpose import ModelPurpose
from src.domain.ports.ai_provider_port import AICapability
from src.infra.services.ai.ai_inference_router import AIInferenceRouter
from src.infra.services.ai.model_route import ModelRoute


class FakeProvider:
    def __init__(self, provider_name, capabilities, result=None, error=None):
        self.provider_name = provider_name
        self.supported_capabilities = capabilities
        self.generate = AsyncMock(return_value=result, side_effect=error)
        self.generate_with_vision = AsyncMock(return_value=result, side_effect=error)

    def get_available_models(self):
        return []

    def extract_error_code(self, error):
        text = str(error).lower()
        if "429" in text:
            return 429
        if "timeout" in text:
            return "timeout"
        return None


@pytest.mark.asyncio
async def test_router_uses_openai_first_for_vision():
    openai = FakeProvider(
        "openai",
        {AICapability.VISION, AICapability.STRUCTURED_OUTPUT},
        result={"dish_name": "Bowl"},
    )
    cloudflare = FakeProvider(
        "cloudflare-workers-ai",
        {AICapability.VISION, AICapability.STRUCTURED_OUTPUT},
        result={"dish_name": "Fallback"},
    )
    router = AIInferenceRouter(
        providers={"openai": openai, "cloudflare-workers-ai": cloudflare},
        routes={
            ModelPurpose.MEAL_SCAN: [
                ModelRoute(provider="openai", model="gpt-5.4-mini-2026-03-17"),
                ModelRoute(provider="cloudflare-workers-ai", model="@cf/google/gemma-4-26b-a4b-it"),
            ]
        },
    )

    result = await router.generate_with_vision(
        purpose=ModelPurpose.MEAL_SCAN,
        prompt="prompt",
        image_data=b"image",
        system_message="system",
    )

    assert result == {"dish_name": "Bowl"}
    openai.generate_with_vision.assert_awaited_once()
    cloudflare.generate_with_vision.assert_not_called()


@pytest.mark.asyncio
async def test_router_falls_back_once_after_transient_failure():
    openai = FakeProvider(
        "openai",
        {AICapability.VISION, AICapability.STRUCTURED_OUTPUT},
        error=RuntimeError("429 rate limit"),
    )
    cloudflare = FakeProvider(
        "cloudflare-workers-ai",
        {AICapability.VISION, AICapability.STRUCTURED_OUTPUT},
        result={"dish_name": "Fallback"},
    )
    router = AIInferenceRouter(
        providers={"openai": openai, "cloudflare-workers-ai": cloudflare},
        routes={
            ModelPurpose.MEAL_SCAN: [
                ModelRoute(provider="openai", model="gpt-5.4-mini-2026-03-17"),
                ModelRoute(provider="cloudflare-workers-ai", model="@cf/google/gemma-4-26b-a4b-it"),
            ]
        },
    )

    result = await router.generate_with_vision(
        purpose=ModelPurpose.MEAL_SCAN,
        prompt="prompt",
        image_data=b"image",
        system_message="system",
    )

    assert result == {"dish_name": "Fallback"}
    openai.generate_with_vision.assert_awaited_once()
    cloudflare.generate_with_vision.assert_awaited_once()
```

- [ ] **Step 2: Run router tests and verify import failure**

Run:

```bash
uv run pytest tests/unit/infra/services/ai/test_ai_inference_router.py -q
```

Expected: fails because router files do not exist.

- [ ] **Step 3: Create provider-neutral purpose enum**

Create `src/domain/model/ai/model_purpose.py`:

```python
"""Provider-neutral AI model purposes."""

from enum import Enum


class ModelPurpose(Enum):
    MEAL_SCAN = "meal_scan"
    INGREDIENT_SCAN = "ingredient_scan"
    PARSE_TEXT = "parse_text"
    BARCODE = "barcode"
    MEAL_NAMES = "meal_names"
    RECIPE = "recipe"
    DISCOVERY = "discovery"
    GENERAL = "general"
```

Export it from `src/domain/model/ai/__init__.py`.

- [ ] **Step 4: Create route object**

Create `src/infra/services/ai/model_route.py`:

```python
"""Route value object for AI provider selection."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
```

- [ ] **Step 5: Create AIInferenceRouter**

Create `src/infra/services/ai/ai_inference_router.py`:

```python
"""Explicit provider+model router for AI inference."""

from __future__ import annotations

import logging
from typing import Any

from src.domain.exceptions.ai_exceptions import AIUnavailableError
from src.domain.model.ai.model_purpose import ModelPurpose
from src.domain.ports.ai_provider_port import AICapability, AIProviderPort
from src.infra.services.ai.model_route import ModelRoute

logger = logging.getLogger(__name__)


class AIInferenceRouter:
    """Routes AI requests through explicit provider+model chains."""

    def __init__(
        self,
        *,
        providers: dict[str, AIProviderPort],
        routes: dict[ModelPurpose, list[ModelRoute]],
    ) -> None:
        self._providers = providers
        self._routes = routes

    def get_routes(self, purpose: ModelPurpose) -> list[ModelRoute]:
        return list(self._routes.get(purpose, self._routes[ModelPurpose.GENERAL]))

    async def generate(
        self,
        *,
        purpose: ModelPurpose,
        prompt: str,
        system_message: str,
        response_type: str = "json",
        max_tokens: int | None = None,
        schema: type | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        routes = self.get_routes(purpose)
        attempted: list[str] = []
        last_error: str | None = None

        for route in routes:
            provider = self._providers.get(route.provider)
            if provider is None:
                continue
            if AICapability.TEXT_GENERATION not in provider.supported_capabilities:
                continue

            attempted.append(f"{route.provider}:{route.model}")
            try:
                return await provider.generate(
                    model=route.model,
                    prompt=prompt,
                    system_message=system_message,
                    response_type=response_type,
                    max_tokens=max_tokens,
                    schema=schema,
                    purpose_hint=purpose.value,
                    **kwargs,
                )
            except Exception as exc:
                last_error = str(exc)
                if not self._is_transient(provider.extract_error_code(exc)):
                    raise
                logger.warning(
                    "[AI-ROUTER-FALLBACK] purpose=%s provider=%s model=%s error=%s",
                    purpose.value,
                    route.provider,
                    route.model,
                    last_error[:160],
                )

        raise AIUnavailableError(
            f"All providers failed for {purpose.value}",
            attempted_models=attempted,
            last_error=last_error,
        )

    async def generate_with_vision(
        self,
        *,
        purpose: ModelPurpose,
        prompt: str,
        image_data: bytes,
        system_message: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        routes = self.get_routes(purpose)
        attempted: list[str] = []
        last_error: str | None = None

        for route in routes:
            provider = self._providers.get(route.provider)
            if provider is None:
                continue
            if AICapability.VISION not in provider.supported_capabilities:
                continue

            attempted.append(f"{route.provider}:{route.model}")
            try:
                return await provider.generate_with_vision(
                    model=route.model,
                    prompt=prompt,
                    image_data=image_data,
                    system_message=system_message,
                    purpose_hint=purpose.value,
                    **kwargs,
                )
            except Exception as exc:
                last_error = str(exc)
                if not self._is_transient(provider.extract_error_code(exc)):
                    raise
                logger.warning(
                    "[AI-VISION-ROUTER-FALLBACK] purpose=%s provider=%s model=%s error=%s",
                    purpose.value,
                    route.provider,
                    route.model,
                    last_error[:160],
                )

        raise AIUnavailableError(
            f"All vision providers failed for {purpose.value}",
            attempted_models=attempted,
            last_error=last_error,
        )

    def _is_transient(self, error_code: int | str | None) -> bool:
        return error_code in {429, 500, 502, 503, 504, "timeout", "connection"}
```

- [ ] **Step 6: Wire routes without changing production default yet**

In `src/infra/services/ai/ai_model_manager.py`, keep the compatibility class for now, but import `ModelPurpose` from `src.domain.model.ai.model_purpose`. Do not infer OpenAI ownership from model prefixes.

Add OpenAI provider only when `settings.OPENAI_API_KEY` is present:

```python
from src.infra.services.ai.providers.openai_provider import OpenAIProvider

if settings.OPENAI_API_KEY:
    self._providers["openai"] = OpenAIProvider(
        api_key=settings.OPENAI_API_KEY,
        request_timeout_seconds=settings.OPENAI_REQUEST_TIMEOUT_SECONDS,
        max_retries=settings.OPENAI_MAX_RETRIES,
        store_responses=settings.OPENAI_STORE_RESPONSES,
    )
```

Default route order must remain Gemini-first until canary:

```python
ModelPurpose.MEAL_SCAN: [
    ModelRoute("gemini", settings.GEMINI_MODEL_NAMES),
]
```

Only use OpenAI-first when `settings.AI_PRIMARY_PROVIDER == "openai"`.

- [ ] **Step 7: Run router tests**

Run:

```bash
uv run pytest tests/unit/infra/services/ai/test_ai_inference_router.py tests/unit/infra/services/ai/test_ai_model_manager.py -q
```

Expected: tests pass.

- [ ] **Step 8: Commit router**

Run:

```bash
git add src/domain/model/ai src/infra/services/ai tests/unit/infra/services/ai
git commit -m "feat: add explicit ai inference routing"
```

Expected: commit succeeds.

### Task 8: OpenAI Embeddings With Versioned Storage

**Files:**
- Create: `src/infra/adapters/openai_text_embedding_adapter.py`
- Modify: `src/api/dependencies/meal_image_cache.py`
- Modify: `scripts/resolve_pending_images.py`
- Modify: `src/infra/database/models/meal_image_cache.py`
- Create: Alembic migration under `alembic/versions/`
- Modify: pgvector cache repositories.
- Test: `tests/unit/infra/adapters/test_openai_text_embedding_adapter.py`
- Test: `tests/unit/api/dependencies/test_meal_image_cache.py`

- [ ] **Step 1: Add OpenAI embedding adapter tests**

Create `tests/unit/infra/adapters/test_openai_text_embedding_adapter.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.infra.adapters.openai_text_embedding_adapter import OpenAITextEmbeddingAdapter


@pytest.mark.asyncio
async def test_embed_text_uses_dimensions_512():
    adapter = OpenAITextEmbeddingAdapter(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=512,
    )
    adapter._client.embeddings.create = AsyncMock(
        return_value=SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[0.1, 0.2]),
                SimpleNamespace(embedding=[0.3, 0.4]),
            ]
        )
    )

    result = await adapter.embed_text(["rice", "chicken"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    call_kwargs = adapter._client.embeddings.create.await_args.kwargs
    assert call_kwargs["model"] == "text-embedding-3-small"
    assert call_kwargs["dimensions"] == 512
    assert call_kwargs["input"] == ["rice", "chicken"]
```

- [ ] **Step 2: Run embedding tests and verify import failure**

Run:

```bash
uv run pytest tests/unit/infra/adapters/test_openai_text_embedding_adapter.py -q
```

Expected: fails because adapter does not exist.

- [ ] **Step 3: Create OpenAI embedding adapter**

Create `src/infra/adapters/openai_text_embedding_adapter.py`:

```python
"""Text embedding adapter backed by OpenAI embeddings."""

from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI


class OpenAITextEmbeddingAdapter:
    """Embed meal-cache text into provider-versioned OpenAI vectors."""

    def __init__(self, *, api_key: str, model: str, dimensions: int) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    async def embed_text(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dimensions,
            encoding_format="float",
        )
        return [item.embedding for item in response.data]


@lru_cache(maxsize=1)
def get_openai_text_embedder(
    api_key: str,
    model: str,
    dimensions: int,
) -> OpenAITextEmbeddingAdapter:
    return OpenAITextEmbeddingAdapter(
        api_key=api_key,
        model=model,
        dimensions=dimensions,
    )
```

- [ ] **Step 4: Add v2 vector columns**

In `src/infra/database/models/meal_image_cache.py`, add:

```python
    text_embedding_v2 = Column(Vector(512), nullable=True)
    embedding_provider = Column(Text, nullable=True)
    embedding_model = Column(Text, nullable=True)
```

Create an Alembic migration with timestamp naming:

```bash
uv run alembic revision -m "meal image cache openai embedding v2"
```

Edit the generated migration to add:

```python
def upgrade() -> None:
    op.add_column("meal_image_cache", sa.Column("text_embedding_v2", Vector(512), nullable=True))
    op.add_column("meal_image_cache", sa.Column("embedding_provider", sa.Text(), nullable=True))
    op.add_column("meal_image_cache", sa.Column("embedding_model", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("meal_image_cache", "embedding_model")
    op.drop_column("meal_image_cache", "embedding_provider")
    op.drop_column("meal_image_cache", "text_embedding_v2")
```

- [ ] **Step 5: Switch new writes to OpenAI v2 without mixing reads**

In `src/api/dependencies/meal_image_cache.py`, replace Gemini text embedder import with:

```python
from src.infra.adapters.openai_text_embedding_adapter import get_openai_text_embedder
```

Replace embedder construction with:

```python
        embedder=get_openai_text_embedder(
            settings.OPENAI_API_KEY,
            settings.OPENAI_EMBEDDING_MODEL,
            settings.OPENAI_EMBEDDING_DIMENSIONS,
        ),
```

Add a startup-safe guard before construction:

```python
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for meal image cache embeddings")
```

- [ ] **Step 6: Update nightly resolver**

In `scripts/resolve_pending_images.py`, replace:

```python
    from src.infra.adapters.gemini_text_embedding_adapter import GeminiTextEmbeddingAdapter
```

with:

```python
    from src.infra.adapters.openai_text_embedding_adapter import OpenAITextEmbeddingAdapter
```

Replace:

```python
    text_embedder = GeminiTextEmbeddingAdapter(api_key=settings.GOOGLE_API_KEY)
```

with:

```python
    text_embedder = OpenAITextEmbeddingAdapter(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_EMBEDDING_MODEL,
        dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS,
    )
```

- [ ] **Step 7: Run embedding tests**

Run:

```bash
uv run pytest \
  tests/unit/infra/adapters/test_openai_text_embedding_adapter.py \
  tests/unit/api/dependencies/test_meal_image_cache.py \
  -q
```

Expected: tests pass after dependency tests expect OpenAI embedder.

- [ ] **Step 8: Commit embeddings v2**

Run:

```bash
git add src/infra/adapters/openai_text_embedding_adapter.py src/api/dependencies/meal_image_cache.py src/infra/database/models/meal_image_cache.py scripts/resolve_pending_images.py alembic/versions tests/unit/infra/adapters/test_openai_text_embedding_adapter.py tests/unit/api/dependencies/test_meal_image_cache.py
git commit -m "feat: add openai embedding vector path"
```

Expected: commit succeeds.

### Task 9: Delete Gemini After Cutover

**Files:**
- Delete Gemini AI files listed in File Structure.
- Modify: `src/api/main.py`
- Modify: `pyproject.toml`
- Modify: `src/infra/config/settings.py`
- Modify: `.env.example`
- Modify: docs and tests with active Gemini provider assumptions.

- [ ] **Step 1: Confirm production gates before deletion**

Run these checks against deploy config and logs before editing:

```bash
rg "AI_PRIMARY_PROVIDER=openai|OPENAI_API_KEY|OPENAI_EMBEDDING_MODEL" .env.example docs scripts src
rg "GOOGLE_API_KEY" src scripts docs .env.example
```

Expected: OpenAI config exists. Remaining `GOOGLE_API_KEY` references are only Gemini AI references or unrelated docs. Do not remove Firebase settings.

- [ ] **Step 2: Remove Gemini startup cache**

In `src/api/main.py`, delete the block starting at:

```python
    # Initialize Gemini explicit context caches
```

through:

```python
            logger.warning(f"Gemini cache warmup failed (non-fatal): {e}")
```

Also delete the shutdown block:

```python
    # Stop Gemini cache refresh loop before disconnecting Redis
    if gemini_cache_manager is not None:
        try:
            await gemini_cache_manager.stop()
        except Exception as e:
            logger.warning(f"Gemini cache manager stop failed: {e}")
```

- [ ] **Step 3: Delete Gemini files**

Run:

```bash
git rm \
  src/infra/services/ai/providers/gemini_provider.py \
  src/infra/services/ai/gemini_model_manager.py \
  src/infra/services/ai/gemini_model_config.py \
  src/infra/services/ai/gemini_cache_manager.py \
  src/infra/services/ai/gemini_cache_handler.py \
  src/infra/ai/gemini_service.py \
  src/infra/adapters/gemini_text_embedding_adapter.py
```

Expected: files are staged for deletion.

- [ ] **Step 4: Remove Gemini dependencies**

In `pyproject.toml`, remove:

```toml
    "langchain-google-genai==4.2.5",
    "google-genai==2.8.0",
```

Run:

```bash
uv sync
```

Expected: lockfile updates without Gemini packages.

- [ ] **Step 5: Remove Gemini AI settings only**

In `src/infra/config/settings.py` and `.env.example`, remove:

```text
GOOGLE_API_KEY
GEMINI_MODEL
GEMINI_MODEL_NAMES
GEMINI_MODEL_RECIPE
CLOUDFLARE_AI_GATEWAY_GEMINI_VISION_ENABLED
```

Keep:

```text
GOOGLE_CLOUD_PROJECT
FIREBASE_CREDENTIALS
FIREBASE_SERVICE_ACCOUNT_JSON
FIREBASE_SERVICE_ACCOUNT_PATH
```

- [ ] **Step 6: Run deletion checks**

Run:

```bash
rg "Gemini|gemini|GOOGLE_API_KEY|langchain-google-genai|google-genai" src tests scripts pyproject.toml .env.example docs
```

Expected: no active Gemini AI references remain. Firebase or historical docs references may remain only if explicitly labeled historical.

- [ ] **Step 7: Run final Gemini deletion tests**

Run:

```bash
uv run python -m compileall -q src tests scripts
uv run pytest tests/unit/infra/services/ai tests/unit/infra/adapters tests/unit/api/dependencies -q
```

Expected: tests pass.

- [ ] **Step 8: Commit Gemini removal**

Run:

```bash
git add -u src tests scripts docs pyproject.toml uv.lock .env.example
git commit -m "refactor: remove gemini ai provider"
```

Expected: commit succeeds.

### Task 10: Nutrition Resolver After Provider Migration

**Files:**
- Create: `src/domain/model/ai/vision_food_identity_contract.py`
- Create: `src/domain/services/nutrition_resolver.py`
- Modify: `src/infra/adapters/vision_ai_service.py`
- Use existing: `src/infra/adapters/food_data_service.py`
- Use existing: `src/infra/adapters/fat_secret_service.py`
- Use existing: `src/infra/adapters/open_food_facts_service.py`
- Test: `tests/unit/domain/services/test_nutrition_resolver.py`

- [ ] **Step 1: Add resolver tests**

Create `tests/unit/domain/services/test_nutrition_resolver.py`:

```python
import pytest

from src.domain.services.nutrition_resolver import NutritionCandidate, NutritionResolver


@pytest.mark.asyncio
async def test_resolver_scales_nutrients_per_100g():
    resolver = NutritionResolver(
        local_candidates={
            "grilled chicken breast": NutritionCandidate(
                name="grilled chicken breast",
                protein_per_100g=31.0,
                carbs_per_100g=0.0,
                fat_per_100g=3.6,
                fiber_per_100g=0.0,
                sugar_per_100g=0.0,
                source="local",
            )
        }
    )

    result = await resolver.resolve_item(
        name="grilled chicken breast",
        estimated_grams=150.0,
    )

    assert result.macros.protein == pytest.approx(46.5)
    assert result.macros.carbs == pytest.approx(0.0)
    assert result.macros.fat == pytest.approx(5.4)
    assert result.source == "local"
```

- [ ] **Step 2: Run resolver tests and verify import failure**

Run:

```bash
uv run pytest tests/unit/domain/services/test_nutrition_resolver.py -q
```

Expected: fails because resolver does not exist.

- [ ] **Step 3: Create identity contract**

Create `src/domain/model/ai/vision_food_identity_contract.py`:

```python
"""Vision output contract for food identity and portion only."""

from pydantic import BaseModel, ConfigDict, Field


class VisionFoodIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    preparation: str | None = Field(None, max_length=120)
    estimated_grams: float = Field(gt=0, le=5000)
    grams_min: float | None = Field(None, gt=0, le=5000)
    grams_max: float | None = Field(None, gt=0, le=5000)
    confidence: float = Field(0.5, ge=0, le=1)


class VisionFoodIdentityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_food: bool = True
    dish_name: str | None = Field(None, max_length=200)
    emoji: str | None = Field(None, max_length=32)
    foods: list[VisionFoodIdentity] = Field(default_factory=list, max_length=8)
    confidence: float = Field(0.5, ge=0, le=1)
```

- [ ] **Step 4: Create deterministic resolver**

Create `src/domain/services/nutrition_resolver.py`:

```python
"""Resolve food identity and grams into deterministic nutrition."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.model.nutrition import FoodItem, Macros


@dataclass(frozen=True)
class NutritionCandidate:
    name: str
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    fiber_per_100g: float = 0.0
    sugar_per_100g: float = 0.0
    source: str = "unknown"


@dataclass(frozen=True)
class ResolvedNutritionItem:
    name: str
    grams: float
    macros: Macros
    source: str


class NutritionResolver:
    """Resolve recognized food names against structured nutrition data."""

    def __init__(self, local_candidates: dict[str, NutritionCandidate]) -> None:
        self._local_candidates = {
            key.strip().lower(): value for key, value in local_candidates.items()
        }

    async def resolve_item(
        self,
        *,
        name: str,
        estimated_grams: float,
    ) -> ResolvedNutritionItem:
        key = name.strip().lower()
        if key not in self._local_candidates:
            raise ValueError(f"No nutrition candidate found for food: {name}")

        candidate = self._local_candidates[key]
        factor = estimated_grams / 100.0
        return ResolvedNutritionItem(
            name=candidate.name,
            grams=estimated_grams,
            macros=Macros(
                protein=round(candidate.protein_per_100g * factor, 2),
                carbs=round(candidate.carbs_per_100g * factor, 2),
                fat=round(candidate.fat_per_100g * factor, 2),
                fiber=round(candidate.fiber_per_100g * factor, 2),
                sugar=round(candidate.sugar_per_100g * factor, 2),
            ),
            source=candidate.source,
        )
```

- [ ] **Step 5: Run resolver tests**

Run:

```bash
uv run pytest tests/unit/domain/services/test_nutrition_resolver.py -q
```

Expected: tests pass.

- [ ] **Step 6: Commit resolver foundation**

Run:

```bash
git add src/domain/model/ai/vision_food_identity_contract.py src/domain/services/nutrition_resolver.py tests/unit/domain/services/test_nutrition_resolver.py
git commit -m "feat: add deterministic nutrition resolver foundation"
```

Expected: commit succeeds.

## Final Verification

- [ ] **Step 1: Run broad AI test suite**

Run:

```bash
uv run pytest \
  tests/unit/domain/model/ai \
  tests/unit/domain/parsers \
  tests/unit/domain/services \
  tests/unit/infra/adapters \
  tests/unit/infra/services/ai \
  tests/unit/api/dependencies \
  -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run compile and lint gates**

Run:

```bash
uv run python -m compileall -q src tests scripts
uv run ruff check src tests
uv run lint-imports
```

Expected: all commands exit 0.

- [ ] **Step 3: Confirm no unsafe Gemini deletion before cutover**

Run before PR 5 only:

```bash
rg "GeminiProvider|GeminiTextEmbeddingAdapter|GOOGLE_API_KEY|gemini_cache" src tests scripts
```

Expected before PR 5: matches exist while Gemini rollback or Gemini embeddings are still active.

Expected after PR 5: no active Gemini AI references remain.

## Self-Review

Spec coverage:
- Contract refactor covered by Tasks 1 through 5.
- OpenAI provider covered by Task 6.
- Traffic switch covered by Task 7.
- Embedding migration covered by Task 8.
- Gemini deletion covered by Task 9.
- Nutrition accuracy covered by Task 10.

Placeholder scan:
- No task uses unspecified placeholders.
- Every code-changing task includes concrete code or command blocks.
- Each test step includes exact command and expected result.

Type consistency:
- Provider-facing image schema name stays `VisionNutritionResponse` until Task 10 introduces `VisionFoodIdentityResponse`.
- Provider route purpose type is `src.domain.model.ai.model_purpose.ModelPurpose`.
- OpenAI embedding dimensions setting is `OPENAI_EMBEDDING_DIMENSIONS`.
- OpenAI provider uses `schema` for structured output and `image_mime_type` for data URLs.

## Execution Handoff

Plan complete. Recommended execution path:

1. Use `superpowers:subagent-driven-development` and dispatch one fresh subagent per task.
2. Review after each task.
3. Keep commits small and stop after PR 1 if production risk or test drift appears.
