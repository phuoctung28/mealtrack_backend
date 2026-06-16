---
phase: 2
title: "AI Core Consolidation"
status: completed
priority: P1
effort: "2-3d"
dependencies: [1]
---

# Phase 2: AI Core Consolidation

## Overview

Collapse the two AI managers + provider into a single `GeminiService`; consolidate all prompts into one registry; merge three JSON extractors into one module; slim vision strategies to thin `{prompt, schema, purpose}` objects. Ships as 2–3 focused PRs (2a, 2b, 2c+2d can be batched).

> **Red Team fix (F3):** Phase 2a must explicitly decide the `VisionAIServicePort` strategy. `GeminiService.vision()` is structurally incompatible with `VisionAIServicePort`'s 6-method interface (`analyze`, `analyze_with_ingredients_context`, etc.). Choose one of the two adapter strategies documented in step 2a below before writing any code.
>
> **Red Team fix (F5):** `UserContextAwareAnalysisStrategy` is live — called from `UploadMealImageImmediatelyHandler:78-86` and `ScanByUrlCommandHandler:96-103`. Phase 2d must NOT delete it. Slim it to `{prompt, schema, purpose}` return like other strategies; keep the class.

## Context Links

- Managers to remove: `src/infra/services/ai/ai_model_manager.py`, `src/infra/services/ai/gemini_model_manager.py`
- Provider to remove: `src/infra/services/ai/providers/` folder + `AIProviderPort`
- Adapter port to update: `src/domain/ports/vision_ai_service_port.py` (see adapter strategy decision)
- DI singleton: `src/api/base_dependencies.py:42,102,111` (`get_vision_service()`)
- Handlers typed on port: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:18,48`, `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py:13`
- Target location: `src/infra/ai/` (new directory)
- Prompt registry: `src/domain/services/prompts/system_prompts.py`
- Inline prompts: `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:263-294`, `src/infra/adapters/brave_search_nutrition_service.py`, `src/domain/strategies/meal_analysis_strategy.py:164-183`, `src/infra/adapters/parallel_recipe_generator.py`
- JSON extractors: `src/infra/adapters/vision_ai_service.py::_extract_json_from_response`, `src/infra/adapters/ai_json_utils.py::extract_json`, `src/infra/adapters/meal_text_parsing_utils.py::extract_json_from_response`
- Live strategies (must keep): `src/domain/strategies/meal_analysis_strategy.py` — `BasicAnalysisStrategy`, `IngredientIdentificationStrategy`, `UserContextAwareAnalysisStrategy`
- Dead strategies (confirm then delete): `CombinedAnalysisStrategy` (grep first)

## Requirements

- Single `GeminiService` with `vision()`, `text_json()`, `embed()` async methods.
- `VisionAIServicePort`/`VisionAIService` adapter relationship explicitly resolved (see step 2a).
- All prompts in `SystemPrompts` with `PROMPT_VERSION` constant.
- One JSON extractor at `src/infra/ai/json_extract.py`.
- `BasicAnalysisStrategy`, `IngredientIdentificationStrategy`, and `UserContextAwareAnalysisStrategy` all slimmed to `{prompt, schema, purpose}` return — none deleted.
- All test mocks target `GeminiService` only.
- `importlinter` passes; no circular imports.

## Architecture

Target layout:

```
src/infra/ai/
├── gemini_service.py         # SINGLE entrypoint: vision(), text_json(), embed()
├── circuit_breaker.py        # moved from provider_circuit_breaker.py
├── context_cache.py          # merged gemini_cache_manager + gemini_cache_handler
├── model_config.py           # purpose→model map, temperature, fallback chain
└── json_extract.py           # one JSON extractor used everywhere
```

`GeminiService` keeps the existing LangChain `ChatGoogleGenerativeAI` pool, circuit breaker, context cache, fallback chain (`gemini-2.5-flash-lite` → `gemini-2.5-flash`).

> **Note on embeddings:** `gemini_text_embedding_adapter.py` uses a separate `GoogleGenerativeAIEmbeddings` LangChain path. `GeminiService.embed()` may delegate to it internally or replace it — either is acceptable. The "single entrypoint" claim applies to the meal AI flows (vision, text_json); the embedding path is an internal detail.

## Implementation Steps

### 2a — Adapter strategy decision (decide before writing code)

**Choose one of the two strategies and document it in the PR description:**

- **Option A (recommended): Keep VisionAIService as thin shell**
  - `VisionAIService` stays; internally calls `GeminiService.vision()` / `GeminiService.text_json()`.
  - `VisionAIServicePort` interface unchanged; all handler injections unchanged.
  - `GeminiService` is an internal implementation detail of `VisionAIService`.
  - `AIModelManager` + `GeminiModelManager` + `GeminiProvider` are deleted (replaced by `GeminiService` inside `VisionAIService`).

- **Option B: Replace VisionAIServicePort with GeminiService**
  - Update `VisionAIServicePort` to match `GeminiService`'s interface.
  - Update all 4+ handler injections and their types.
  - Higher risk; requires mypy to catch every missed reference.

**Proceed with chosen option. Do NOT leave this decision unresolved.**

### 2a (continued) — Collapse managers into `GeminiService` (1 PR)

1. Create `src/infra/ai/` directory.
2. Write `src/infra/ai/gemini_service.py` implementing:
   - `async vision(purpose, image_bytes, prompt, schema) -> BaseModel`
   - `async text_json(purpose, user_prompt, system_prompt, schema) -> BaseModel`
   - `async embed(text) -> list[float]`
   - Internal: pool, circuit breaker, context cache, fallback chain.
3. Move `circuit_breaker.py`, `context_cache.py` logic into `src/infra/ai/`.
4. Write `src/infra/ai/model_config.py` with purpose→model map.
5. Wire `GeminiService` into `VisionAIService` (Option A) or replace port (Option B) per decision above.
6. Update DI: `src/api/base_dependencies.py:42,102,111`.
7. Delete `AIModelManager`, `GeminiModelManager`, `GeminiProvider`, `AIProviderPort`, `providers/` folder.
8. Run `pytest` + `mypy src` to confirm injection wiring is clean.

### 2b — One prompt registry (1 PR)

1. Add to `SystemPrompts`:
   - `BARCODE_AI_ESTIMATE` (from `lookup_barcode_query_handler.py:263-294`)
   - `BARCODE_BRAVE_EXTRACT` (from `brave_search_nutrition_service.py`)
   - `INGREDIENT_IDENTIFY` (from `meal_analysis_strategy.py:164-183`)
   - `DISCOVERY_SYSTEM`, `MEAL_NAMES_SYSTEM` (from `parallel_recipe_generator.py`)
2. Add `PROMPT_VERSION = "2026-06-16"` constant.
3. Delete inline prompt strings from callers; import from `SystemPrompts`.

### 2c — One JSON extractor (batch with 2d)

1. Write `src/infra/ai/json_extract.py` with the best logic from all three extractors.
2. Delete `ai_json_utils.py::extract_json` and `meal_text_parsing_utils.py::extract_json_from_response`.
3. Remove `_extract_json_from_response` from `vision_ai_service.py`.
4. All callers import from `src.infra.ai.json_extract`.

### 2d — Slim vision strategies (batch with 2c)

1. Grep to confirm `CombinedAnalysisStrategy` has zero callers → delete it.
2. **Do NOT delete `UserContextAwareAnalysisStrategy`** — it is live in both `UploadMealImageImmediatelyHandler:78-86` and `ScanByUrlCommandHandler:96-103`.
3. Slim all three kept strategies (`BasicAnalysisStrategy`, `IngredientIdentificationStrategy`, `UserContextAwareAnalysisStrategy`) to return `{prompt, schema, purpose}` only.

## Related Code Files

- Create: `src/infra/ai/gemini_service.py`, `src/infra/ai/circuit_breaker.py`, `src/infra/ai/context_cache.py`, `src/infra/ai/model_config.py`, `src/infra/ai/json_extract.py`
- Modify: `src/domain/services/prompts/system_prompts.py`
- Modify: `src/domain/strategies/meal_analysis_strategy.py` (slim 3 strategies; delete CombinedAnalysisStrategy)
- Modify: `src/infra/adapters/vision_ai_service.py` (delegate to GeminiService or per Option B)
- Modify: `src/api/base_dependencies.py` (DI wiring)
- Modify: all handlers/adapters that call old managers
- Delete: `src/infra/services/ai/ai_model_manager.py`, `src/infra/services/ai/gemini_model_manager.py`, `src/infra/services/ai/providers/`, `src/domain/ports/ai_provider_port.py`

## Success Criteria

- [ ] `pytest` passes; all existing AI tests pass with mocks targeting `GeminiService` only.
- [ ] `ruff check src tests` and `mypy src` pass.
- [ ] `importlinter` passes; no circular imports.
- [ ] `grep -r "AIModelManager\|GeminiModelManager\|AIProviderPort" src tests` returns zero hits.
- [ ] All prompts have a name constant in `SystemPrompts`; no inline prompt strings remain in handler/adapter files.
- [ ] Exactly one JSON extractor in codebase (`src/infra/ai/json_extract.py`).
- [ ] `UserContextAwareAnalysisStrategy` still exists and is callable from both handler call sites.
- [ ] Adapter strategy decision (Option A or B) documented in PR description.

## Risk Assessment

Medium risk. The adapter strategy decision (step 2a) is the single highest-risk choice in this phase — resolve it before writing code to avoid rewriting handler injections twice. Ship 2a first (GeminiService + adapter wiring), then 2b+2c+2d can follow as non-breaking prompt/extractor consolidation.
