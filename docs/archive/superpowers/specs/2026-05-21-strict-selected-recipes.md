# Strict Selected Recipe Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make selected meal recipe generation return exactly one recipe per selected discovery meal, using the richer mobile payload, structured recipe output, cleaner prompts, and controlled retryable backend errors.

**Architecture:** Mobile will build one full selected-discovery recipe request from selected discovery ids and meal objects, even when only one cache slot is missing. Backend will route selected-discovery requests through strict selected generation, use `RecipeDetailsResponse` structured output for recipe details, retry failed selected slots internally, and convert generation failures to `ExternalServiceException`/503 instead of unexpected 500s.

**Tech Stack:** FastAPI, Pydantic, pytest, asyncio, Flutter/Dart, Riverpod, Freezed models, flutter_test.

---

## File Structure

Backend files:

- Modify `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/ai/schemas.py`
  - Extend `RecipeDetailsResponse` with optional `origin_country`, `cuisine_type`, and `emoji`.
  - Update comments so production schema usage is accurate.
- Modify `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/prompts/prompt_constants.py`
  - Align `JSON_SCHEMAS["suggestion_recipe"]` with the structured recipe schema.
- Modify `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/prompts/prompt_template_manager.py`
  - Remove contradictory ingredient wording.
  - Use conditional ingredient instructions for empty and non-empty ingredient lists.
- Modify `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/recipe_attempt_builder.py`
  - Accept an optional recipe schema and pass it to `generate_meal_plan`.
- Modify `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/parallel_recipe_generator.py`
  - Store the injected recipe details schema.
  - Use schema-backed generation.
  - Make selected generation strict all-or-nothing with internal retries and order preservation.
- Modify `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/suggestion_orchestration_service.py`
  - Accept and pass `recipe_details_schema_class`.
- Modify `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/base_dependencies.py`
  - Inject `RecipeDetailsResponse`.
- Modify `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/meal_suggestion/generate_meal_recipes_command_handler.py`
  - Wrap recipe generation failures as `ExternalServiceException`.
  - Verify strict selected count before translation.
- Modify backend tests:
  - `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/services/ai/test_schemas.py`
  - `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/test_suggestion_prompt_builder.py`
  - `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py`
  - `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py`
  - `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py`
  - `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_meal_suggestions_routes.py`

Mobile files:

- Create `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/meal_suggestion/application/utils/recipe_request_payload.dart`
  - Build the selected recipe request map with explicit JSON-safe `selected_meals`.
- Modify `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/meal_suggestion/application/providers/meal_suggestion_flow_provider.dart`
  - Use the new request builder and send the full selected batch during recipe retries.
- Create `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/test/features/meal_suggestion/application/recipe_request_payload_test.dart`
  - Test payload shape and full-batch retry semantics at the pure helper level.

---

### Task 1: Backend Strict Selected Generation Tests

**Files:**
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_meal_suggestions_routes.py`

- [ ] **Step 1: Add failing generator tests for all-or-nothing selected recipes**

Append these tests to `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py`:

```python
@pytest.mark.asyncio
async def test_selected_recipes_retry_failed_slot_and_return_full_batch_in_order():
    selected_meals = [
        {
            "id": "disc_a",
            "name": "Ginger Chicken Rice",
            "english_name": "Ginger Chicken Rice",
            "calories": 450,
            "protein": 35,
            "carbs": 45,
            "fat": 12,
        },
        {
            "id": "disc_b",
            "name": "Lemon Salmon Bowl",
            "english_name": "Lemon Salmon Bowl",
            "calories": 520,
            "protein": 38,
            "carbs": 50,
            "fat": 18,
        },
    ]
    session = make_session()
    generator = make_generator()
    calls: dict[str, int] = {}

    async def fake_generate_with_retry(
        prompt: str,
        meal_name: str,
        index: int,
        recipe_system: str,
        session: SuggestionSession,
        reject_on_scale_out_of_range: bool = True,
        fill_missing_steps: bool = False,
    ) -> Optional[MealSuggestion]:
        calls[meal_name] = calls.get(meal_name, 0) + 1
        if meal_name == "Lemon Salmon Bowl" and calls[meal_name] == 1:
            return None
        return make_meal_suggestion(meal_name, index)

    with patch.object(
        generator, "_generate_with_retry", side_effect=fake_generate_with_retry
    ):
        with patch(
            "src.domain.services.meal_suggestion.suggestion_prompt_builder"
            ".build_recipe_details_prompt",
            return_value="mock-prompt",
        ):
            results = await generator.generate_selected_recipes(session, selected_meals)

    assert [r.meal_name for r in results] == [
        "Ginger Chicken Rice",
        "Lemon Salmon Bowl",
    ]
    assert calls["Lemon Salmon Bowl"] == 2


@pytest.mark.asyncio
async def test_selected_recipes_raise_when_any_slot_still_fails():
    selected_meals = [
        {
            "id": "disc_a",
            "name": "Ginger Chicken Rice",
            "english_name": "Ginger Chicken Rice",
            "calories": 450,
            "protein": 35,
            "carbs": 45,
            "fat": 12,
        },
        {
            "id": "disc_b",
            "name": "Lemon Salmon Bowl",
            "english_name": "Lemon Salmon Bowl",
            "calories": 520,
            "protein": 38,
            "carbs": 50,
            "fat": 18,
        },
    ]
    session = make_session()
    generator = make_generator()

    async def fake_generate_with_retry(
        prompt: str,
        meal_name: str,
        index: int,
        recipe_system: str,
        session: SuggestionSession,
        reject_on_scale_out_of_range: bool = True,
        fill_missing_steps: bool = False,
    ) -> Optional[MealSuggestion]:
        if meal_name == "Lemon Salmon Bowl":
            return None
        return make_meal_suggestion(meal_name, index)

    with patch.object(
        generator, "_generate_with_retry", side_effect=fake_generate_with_retry
    ):
        with patch(
            "src.domain.services.meal_suggestion.suggestion_prompt_builder"
            ".build_recipe_details_prompt",
            return_value="mock-prompt",
        ):
            with pytest.raises(RuntimeError) as exc:
                await generator.generate_selected_recipes(session, selected_meals)

    assert "Failed to generate all selected recipes" in str(exc.value)
    assert "disc_b" in str(exc.value)
```

- [ ] **Step 2: Add failing handler test for strict selected count**

Append this test to `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py`:

```python
@pytest.mark.asyncio
async def test_generate_meal_recipes_handler_rejects_selected_count_mismatch():
    discovery_session = SuggestionSession(
        id="sess-discovery",
        user_id="user-1",
        meal_type="lunch",
        meal_portion_type="main",
        target_calories=500,
        ingredients=["carp"],
        cooking_time_minutes=30,
        discovery_meals=[
            {
                "id": "disc_a",
                "name": "Ginger Carp",
                "english_name": "Ginger Carp",
                "calories": 300,
                "protein": 32,
                "carbs": 18,
                "fat": 10,
            },
            {
                "id": "disc_b",
                "name": "Grilled Carp",
                "english_name": "Grilled Carp",
                "calories": 350,
                "protein": 35,
                "carbs": 20,
                "fat": 12,
            },
        ],
    )
    service = AsyncMock()
    service._repo.get_session.return_value = discovery_session
    service._recipe_generator.generate_selected_recipes.return_value = [
        _recipe("r1", "Ginger Carp", 300)
    ]

    from src.api.exceptions import ExternalServiceException

    with pytest.raises(ExternalServiceException) as exc:
        await GenerateMealRecipesCommandHandler(service).handle(
            GenerateMealRecipesCommand(
                user_id="user-1",
                meal_type="lunch",
                language="en",
                session_id="sess-discovery",
                selected_meal_ids=["disc_a", "disc_b"],
            )
        )

    assert exc.value.error_code == "RECIPE_GENERATION_FAILED"
```

- [ ] **Step 3: Add failing route test for controlled 503**

Append this test to `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_meal_suggestions_routes.py`:

```python
def test_generate_recipes_generation_failure_returns_503(ms_client):
    client, _bus = ms_client

    class _BusRecipeFailure:
        async def send(self, msg):
            from src.api.exceptions import ExternalServiceException

            raise ExternalServiceException(
                "Could not generate recipes. Please retry.",
                error_code="RECIPE_GENERATION_FAILED",
                details={"requested": 3, "generated": 0},
            )

    client.app.dependency_overrides[get_configured_event_bus] = (
        lambda: _BusRecipeFailure()
    )

    payload = {
        "session_id": "sess-discovery",
        "selected_meal_ids": ["disc_a", "disc_b", "disc_c"],
        "selected_meals": [
            {
                "id": "disc_a",
                "meal_name": "Ginger Chicken Rice",
                "english_name": "Ginger Chicken Rice",
                "macros": {
                    "calories": 450,
                    "protein": 35,
                    "carbs": 45,
                    "fat": 12,
                },
            },
            {
                "id": "disc_b",
                "meal_name": "Lemon Salmon Bowl",
                "english_name": "Lemon Salmon Bowl",
                "macros": {
                    "calories": 520,
                    "protein": 38,
                    "carbs": 50,
                    "fat": 18,
                },
            },
            {
                "id": "disc_c",
                "meal_name": "Tofu Vegetable Noodles",
                "english_name": "Tofu Vegetable Noodles",
                "macros": {
                    "calories": 430,
                    "protein": 28,
                    "carbs": 55,
                    "fat": 11,
                },
            },
        ],
        "meal_names": [
            "Ginger Chicken Rice",
            "Lemon Salmon Bowl",
            "Tofu Vegetable Noodles",
        ],
        "meal_type": "lunch",
    }

    response = client.post("/v1/meal-suggestions/recipes", json=payload)

    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "RECIPE_GENERATION_FAILED"
```

- [ ] **Step 4: Run backend tests and verify failures**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
pytest tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py tests/unit/api/test_meal_suggestions_routes.py -q
```

Expected: FAIL. The generator test fails because selected generation does not retry failed slots. The handler count mismatch test fails because the handler does not enforce selected count. The route 503 test may pass once it uses existing `ExternalServiceException`, but it still locks the API contract.

- [ ] **Step 5: Commit failing tests**

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
git add tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py tests/unit/api/test_meal_suggestions_routes.py
git commit -m "test: cover strict selected recipe generation"
```

---

### Task 2: Backend Prompt And Schema Tests

**Files:**
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/services/ai/test_schemas.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/test_suggestion_prompt_builder.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py`

- [ ] **Step 1: Add failing schema test for optional metadata**

Append this test to `TestRecipeDetailsResponse` in `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/services/ai/test_schemas.py`:

```python
    def test_accepts_optional_recipe_metadata(self):
        response = RecipeDetailsResponse(
            ingredients=[
                IngredientItem(name="Chicken breast", amount=180, unit="g"),
                IngredientItem(name="Rice", amount=160, unit="g"),
                IngredientItem(name="Ginger", amount=8, unit="g"),
            ],
            recipe_steps=[
                RecipeStepItem(step=1, instruction="Cook rice", duration_minutes=12),
                RecipeStepItem(step=2, instruction="Cook chicken", duration_minutes=10),
            ],
            prep_time_minutes=25,
            origin_country="Vietnam",
            cuisine_type="Vietnamese",
            emoji="🍚",
        )

        assert response.origin_country == "Vietnam"
        assert response.cuisine_type == "Vietnamese"
        assert response.emoji == "🍚"
```

- [ ] **Step 2: Add failing prompt tests for conditional ingredients**

Append these tests to `TestBuildRecipeDetailsPrompt` in `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/test_suggestion_prompt_builder.py`:

```python
    def test_empty_ingredients_prompt_uses_common_ingredients(self, mock_session):
        mock_session.ingredients = []

        prompt = build_recipe_details_prompt("Tomato Egg Rice", mock_session)

        assert "Use common ingredients appropriate for the dish." in prompt
        assert "MUST include user's ingredients" not in prompt
        assert "any ingredients" not in prompt

    def test_non_empty_ingredients_prompt_uses_compatible_wording(self, mock_session):
        prompt = build_recipe_details_prompt("Chicken Rice Bowl", mock_session)

        assert "Use these ingredients as main components where compatible" in prompt
        assert "MUST include user's ingredients" not in prompt
        assert "no substitutions" not in prompt.lower()
```

- [ ] **Step 3: Add failing generator schema wiring test**

Append this test to `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py`:

```python
@pytest.mark.asyncio
async def test_generate_with_retry_passes_recipe_details_schema_to_generation_service():
    from src.infra.services.ai.schemas import RecipeDetailsResponse

    session = make_session()
    generator = make_generator()
    generator._recipe_details_schema = RecipeDetailsResponse

    raw_recipe = {
        "ingredients": [
            {"name": "chicken breast", "amount": 180, "unit": "g"},
            {"name": "rice", "amount": 160, "unit": "g"},
            {"name": "ginger", "amount": 8, "unit": "g"},
        ],
        "recipe_steps": [
            {"step": 1, "instruction": "Cook rice.", "duration_minutes": 12},
            {"step": 2, "instruction": "Cook chicken.", "duration_minutes": 10},
        ],
        "prep_time_minutes": 25,
    }
    generator._generation.generate_meal_plan.return_value = raw_recipe

    meal_macros = MagicMock()
    meal_macros.calories = 450
    meal_macros.protein = 35
    meal_macros.carbs = 45
    meal_macros.fat = 12
    meal_macros.ingredients = []
    meal_macros.t1_count = 3
    meal_macros.t2_count = 0
    meal_macros.t3_count = 0
    generator._nutrition_lookup.calculate_meal_macros = AsyncMock(
        return_value=meal_macros
    )
    generator._nutrition_lookup.scale_to_target.return_value = meal_macros
    generator._macro_validator.validate_deterministic.return_value = meal_macros

    result = await generator._generate_with_retry(
        "prompt",
        "Ginger Chicken Rice",
        0,
        "system",
        session,
    )

    assert result is not None
    first_call = generator._generation.generate_meal_plan.call_args_list[0]
    assert first_call.args[4] is RecipeDetailsResponse
```

- [ ] **Step 4: Run tests and verify failures**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
pytest tests/unit/infra/services/ai/test_schemas.py tests/unit/domain/services/test_suggestion_prompt_builder.py tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py -q
```

Expected: FAIL. The schema metadata test fails because `RecipeDetailsResponse` lacks those fields. The prompt tests fail on current wording. The schema wiring test fails because production recipe calls pass `None` as schema.

- [ ] **Step 5: Commit failing tests**

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
git add tests/unit/infra/services/ai/test_schemas.py tests/unit/domain/services/test_suggestion_prompt_builder.py tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py
git commit -m "test: cover recipe prompt and schema contract"
```

---

### Task 3: Backend Implementation

**Files:**
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/ai/schemas.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/prompts/prompt_constants.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/prompts/prompt_template_manager.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/recipe_attempt_builder.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/parallel_recipe_generator.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/suggestion_orchestration_service.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/base_dependencies.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/meal_suggestion/generate_meal_recipes_command_handler.py`

- [ ] **Step 1: Extend `RecipeDetailsResponse` metadata**

In `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/ai/schemas.py`, replace the `RecipeDetailsResponse` docstring comment and append metadata fields after `prep_time_minutes`:

```python
class RecipeDetailsResponse(BaseModel):
    """Phase 2: Complete recipe details for a meal.

    Macros are optional and ignored by production recipe assembly.
    Deterministic macros are calculated from ingredients via NutritionLookupService.
    """

    ingredients: List[IngredientItem] = Field(
        description="List of 3-8 ingredients with exact amounts",
        min_length=3,
        max_length=8,
    )
    recipe_steps: List[RecipeStepItem] = Field(
        description="List of 2-6 recipe steps with instructions and durations",
        min_length=2,
        max_length=6,
    )
    prep_time_minutes: int = Field(
        description="Total preparation and cooking time in minutes", ge=5, le=120
    )
    origin_country: Optional[str] = Field(
        default=None, description="Country or region of origin"
    )
    cuisine_type: Optional[str] = Field(
        default=None, description="Cuisine style such as Vietnamese or Mediterranean"
    )
    emoji: Optional[str] = Field(default=None, description="Single food emoji")
    calories: Optional[int] = Field(
        default=None, description="AI-reported calories (ignored)"
    )
    protein: Optional[float] = Field(
        default=None, description="AI-reported protein (ignored)"
    )
    carbs: Optional[float] = Field(
        default=None, description="AI-reported carbs (ignored)"
    )
    fat: Optional[float] = Field(default=None, description="AI-reported fat (ignored)")
```

- [ ] **Step 2: Align prompt schema example**

In `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/prompts/prompt_constants.py`, replace `JSON_SCHEMAS["suggestion_recipe"]` with:

```python
    "suggestion_recipe": """{
  "emoji": "🍚",
  "cuisine_type": "Vietnamese",
  "origin_country": "Vietnam",
  "ingredients": [
    {"name": "ingredient1", "amount": 200, "unit": "g"},
    {"name": "ingredient2", "amount": 100, "unit": "g"},
    {"name": "ingredient3", "amount": 50, "unit": "g"}
  ],
  "recipe_steps": [
    {"step": 1, "instruction": "Action", "duration_minutes": 5},
    {"step": 2, "instruction": "Action", "duration_minutes": 10}
  ],
  "prep_time_minutes": 20
}""",
```

- [ ] **Step 3: Clean conditional ingredient prompt wording**

In `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/prompts/prompt_template_manager.py`, replace the ingredient setup and requirement text in `build_recipe_details_prompt` with this shape:

```python
        ingredients = ingredients or []
        ing_str = ", ".join(ingredients[:6])
        if ing_str:
            ingredient_instruction = (
                f"Use these ingredients as main components where compatible: {ing_str}"
            )
            ingredient_requirement = (
                f"- Include compatible user ingredients from this list when they fit the dish: {ing_str}"
            )
        else:
            ingredient_instruction = "Use common ingredients appropriate for the dish."
            ingredient_requirement = "- Use common ingredients appropriate for the dish."
```

Then update the returned prompt body so the top ingredient line and requirement use the new variables:

```python
        return f"""Generate complete recipe for: "{meal_name}"

{ingredient_instruction}{' | ' + constraints_str if constraints_str else ''}
Target:{servings_str} — ~{target_calories} cal{time_str}{equipment_str}{cuisine_str}{macro_target_str}{low_calorie_str}

CRITICAL: Size all quantities for {servings} serving only — no batch scaling.

REQUIREMENTS:
- Match name "{meal_name}" exactly
{ingredient_requirement}
- 3-8 ingredients in GRAMS, scaled for {servings} serving{'s' if servings > 1 else ''}{time_req_str}
- Include origin_country and cuisine_type in JSON

{DECOMPOSITION_RULES}

{EMOJI_RULES}

OUTPUT JSON:
{cls.get_json_schema("suggestion_recipe")}
Return ONLY valid JSON, no markdown.
"""
```

- [ ] **Step 4: Pass recipe schema through attempt generation**

In `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/recipe_attempt_builder.py`, add a parameter to `attempt_recipe_generation`:

```python
    recipe_schema: type | None = None,
```

Then replace the `None` schema argument in the `generate_meal_plan` call:

```python
                recipe_schema,
```

The surrounding call remains:

```python
                generation_service.generate_meal_plan,
                prompt,
                recipe_system,
                "json",
                PARALLEL_SINGLE_MEAL_TOKENS,
                recipe_schema,
                model_purpose,
```

- [ ] **Step 5: Inject and store recipe details schema**

In `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/parallel_recipe_generator.py`, extend `ParallelRecipeGenerator.__init__`:

```python
        recipe_details_schema_class: type | None = None,
```

Set the field:

```python
        self._recipe_details_schema = recipe_details_schema_class
```

In `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/suggestion_orchestration_service.py`, extend the constructor:

```python
        recipe_details_schema_class: type | None = None,
```

Pass it into `ParallelRecipeGenerator`:

```python
            recipe_details_schema_class=recipe_details_schema_class,
```

In `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/base_dependencies.py`, import and pass `RecipeDetailsResponse`:

```python
    from src.infra.services.ai.schemas import (
        DiscoveryMealsResponse,
        MealNamesResponse,
        RecipeDetailsResponse,
    )
```

```python
        recipe_details_schema_class=RecipeDetailsResponse,
```

- [ ] **Step 6: Use schema in both recipe model attempts**

In `_generate_with_retry` in `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/parallel_recipe_generator.py`, pass `self._recipe_details_schema` to both `attempt_recipe_generation` calls:

```python
            recipe_schema=self._recipe_details_schema,
```

Keep `_generate_with_retry`'s public signature unchanged so existing test patches keep working.

- [ ] **Step 7: Replace selected generation with strict retry loop**

In `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/parallel_recipe_generator.py`, replace the body of `generate_selected_recipes` after `recipe_system` with:

```python
        async def generate_one(index: int, selected: dict) -> Optional[MealSuggestion]:
            target_calories = int(selected.get("calories") or session.target_calories)
            recipe_session = replace(
                session,
                target_calories=target_calories,
                protein_target=selected.get("protein") or session.protein_target,
                carbs_target=selected.get("carbs") or session.carbs_target,
                fat_target=selected.get("fat") or session.fat_target,
            )
            meal_name = selected.get("english_name") or selected.get("name")
            if not meal_name:
                raise ValueError("selected meal is missing english_name/name")
            prompt = build_recipe_details_prompt(meal_name, recipe_session)
            return await self._generate_with_retry(
                prompt,
                meal_name,
                index,
                recipe_system,
                recipe_session,
                reject_on_scale_out_of_range=False,
                fill_missing_steps=True,
            )

        results: list[Optional[MealSuggestion]] = [None] * len(selected_meals)
        failures: dict[int, str] = {}
        max_passes = 2

        for pass_number in range(1, max_passes + 1):
            pending = [
                index for index, result in enumerate(results) if result is None
            ]
            if not pending:
                break

            tasks = [
                asyncio.create_task(generate_one(index, selected_meals[index]))
                for index in pending
            ]
            pass_results = await asyncio.gather(*tasks, return_exceptions=True)

            for index, result in zip(pending, pass_results):
                selected_id = selected_meals[index].get("id") or f"index_{index}"
                if isinstance(result, Exception):
                    failures[index] = f"{selected_id}: {type(result).__name__}"
                    logger.warning(
                        "[SELECTED-RECIPE-FAIL] pass=%d | index=%d | id=%s | %s",
                        pass_number,
                        index,
                        selected_id,
                        result,
                    )
                elif result is None:
                    failures[index] = f"{selected_id}: empty result"
                    logger.warning(
                        "[SELECTED-RECIPE-EMPTY] pass=%d | index=%d | id=%s",
                        pass_number,
                        index,
                        selected_id,
                    )
                else:
                    results[index] = result
                    failures.pop(index, None)

        if any(result is None for result in results):
            failure_summary = "; ".join(
                failures[index]
                for index, result in enumerate(results)
                if result is None and index in failures
            )
            raise RuntimeError(
                "Failed to generate all selected recipes: " + failure_summary
            )

        return [result for result in results if result is not None]
```

- [ ] **Step 8: Convert handler failures to controlled 503**

In `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/meal_suggestion/generate_meal_recipes_command_handler.py`, update imports:

```python
from src.api.exceptions import (
    ExternalServiceException,
    ResourceNotFoundException,
    ValidationException,
)
```

Wrap generation and enforce count:

```python
        try:
            if selected_meals:
                recipes = await self.service._recipe_generator.generate_selected_recipes(
                    session, selected_meals
                )
                if len(recipes) != len(selected_meals):
                    raise RuntimeError(
                        f"Expected {len(selected_meals)} selected recipes, got {len(recipes)}"
                    )
            else:
                recipes = await self.service._recipe_generator._phase2_generate_recipes(
                    session,
                    command.meal_names,
                    "English",
                    suggestion_count=len(command.meal_names),
                    min_acceptable_override=1,
                )
        except RuntimeError as exc:
            requested = len(selected_meals) if selected_meals else len(command.meal_names)
            raise ExternalServiceException(
                "Could not generate recipes. Please retry.",
                error_code="RECIPE_GENERATION_FAILED",
                details={
                    "requested": requested,
                    "reason": str(exc),
                },
            ) from exc
```

- [ ] **Step 9: Update constructor call sites in tests**

Every test helper that creates `ParallelRecipeGenerator` or `SuggestionOrchestrationService` must pass the new schema.

Example for `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py`:

```python
    from src.infra.services.ai.schemas import (
        DiscoveryMealsResponse,
        MealNamesResponse,
        RecipeDetailsResponse,
    )
```

```python
        recipe_details_schema_class=RecipeDetailsResponse,
```

Apply the same pattern to:

- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py`
- `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/services/test_suggestion_orchestration_service.py`

- [ ] **Step 10: Run backend tests and verify pass**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
pytest tests/unit/infra/services/ai/test_schemas.py tests/unit/domain/services/test_suggestion_prompt_builder.py tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py tests/unit/api/test_meal_suggestions_routes.py -q
```

Expected: PASS.

- [ ] **Step 11: Commit backend implementation**

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
git add src/infra/services/ai/schemas.py src/domain/services/prompts/prompt_constants.py src/domain/services/prompts/prompt_template_manager.py src/domain/services/meal_suggestion/recipe_attempt_builder.py src/domain/services/meal_suggestion/parallel_recipe_generator.py src/domain/services/meal_suggestion/suggestion_orchestration_service.py src/api/base_dependencies.py src/app/handlers/command_handlers/meal_suggestion/generate_meal_recipes_command_handler.py tests/unit/infra/services/ai/test_schemas.py tests/unit/domain/services/test_suggestion_prompt_builder.py tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py tests/unit/domain/services/test_suggestion_orchestration_service.py tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py tests/unit/api/test_meal_suggestions_routes.py
git commit -m "fix: enforce strict selected recipe generation"
```

---

### Task 4: Mobile Recipe Request Payload Helper

**Files:**
- Create: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/meal_suggestion/application/utils/recipe_request_payload.dart`
- Create: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/test/features/meal_suggestion/application/recipe_request_payload_test.dart`

- [ ] **Step 1: Write failing helper tests**

Create `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/test/features/meal_suggestion/application/recipe_request_payload_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:nutree_ai/features/meal_suggestion/application/utils/recipe_request_payload.dart';
import 'package:nutree_ai/features/meal_suggestion/data/models/discovery_meal_response.dart';

DiscoveryMealResponse _meal({
  required String id,
  required String mealName,
  String? englishName,
  double calories = 450,
  double protein = 35,
  double carbs = 45,
  double fat = 12,
}) {
  return DiscoveryMealResponse(
    id: id,
    mealName: mealName,
    englishName: englishName,
    macros: DiscoveryMacros(
      calories: calories,
      protein: protein,
      carbs: carbs,
      fat: fat,
    ),
  );
}

void main() {
  group('buildSelectedRecipeRequest', () {
    test('sends full selected batch with ids, meals, and names', () {
      final selected = [
        _meal(
          id: 'disc_a',
          mealName: 'Cơm gà gừng',
          englishName: 'Ginger Chicken Rice',
        ),
        _meal(
          id: 'disc_b',
          mealName: 'Lemon Salmon Bowl',
          englishName: 'Lemon Salmon Bowl',
          calories: 520,
          protein: 38,
          carbs: 50,
          fat: 18,
        ),
      ];

      final payload = buildSelectedRecipeRequest(
        selected: selected,
        discoverySessionId: 'sess-discovery',
        mealType: 'lunch',
        calorieTarget: 500,
        cuisineRegion: 'vietnamese',
        ingredients: ['chicken', 'rice'],
        proteinTarget: 40,
        carbsTarget: 55,
        fatTarget: 15,
      );

      expect(payload['session_id'], 'sess-discovery');
      expect(payload['selected_meal_ids'], ['disc_a', 'disc_b']);
      expect(payload['meal_names'], [
        'Ginger Chicken Rice',
        'Lemon Salmon Bowl',
      ]);
      expect(payload['meal_type'], 'lunch');
      expect(payload['calorie_target'], 500);
      expect(payload['cuisine_region'], 'vietnamese');
      expect(payload['ingredients'], ['chicken', 'rice']);
      expect(payload['protein_target'], 40.0);
      expect(payload['carbs_target'], 55.0);
      expect(payload['fat_target'], 15.0);

      final selectedMeals = payload['selected_meals'] as List<Map<String, dynamic>>;
      expect(selectedMeals.length, 2);
      expect(selectedMeals[0]['id'], 'disc_a');
      expect(selectedMeals[0]['meal_name'], 'Cơm gà gừng');
      expect(selectedMeals[0]['english_name'], 'Ginger Chicken Rice');
      expect(selectedMeals[0]['macros'], {
        'calories': 450.0,
        'protein': 35.0,
        'carbs': 45.0,
        'fat': 12.0,
      });
    });

    test('falls back to display name when english name is absent', () {
      final payload = buildSelectedRecipeRequest(
        selected: [_meal(id: 'disc_a', mealName: 'Tomato Egg Rice')],
        discoverySessionId: null,
        mealType: 'breakfast',
      );

      expect(payload.containsKey('session_id'), isFalse);
      expect(payload['meal_names'], ['Tomato Egg Rice']);
      final selectedMeals = payload['selected_meals'] as List<Map<String, dynamic>>;
      expect(selectedMeals[0]['english_name'], 'Tomato Egg Rice');
    });
  });
}
```

- [ ] **Step 2: Run helper tests and verify failure**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
flutter test test/features/meal_suggestion/application/recipe_request_payload_test.dart
```

Expected: FAIL because `recipe_request_payload.dart` does not exist.

- [ ] **Step 3: Implement payload helper**

Create `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/meal_suggestion/application/utils/recipe_request_payload.dart`:

```dart
import 'package:nutree_ai/features/meal_suggestion/data/models/discovery_meal_response.dart';

Map<String, dynamic> buildSelectedRecipeRequest({
  required List<DiscoveryMealResponse> selected,
  required String? discoverySessionId,
  required String mealType,
  int? calorieTarget,
  String? cuisineRegion,
  List<String> ingredients = const [],
  int? proteinTarget,
  int? carbsTarget,
  int? fatTarget,
}) {
  final mealNames = selected
      .map((meal) => meal.englishName ?? meal.mealName)
      .toList(growable: false);

  final selectedMeals = selected
      .map(
        (meal) => <String, dynamic>{
          'id': meal.id,
          'meal_name': meal.mealName,
          'english_name': meal.englishName ?? meal.mealName,
          'macros': <String, dynamic>{
            'calories': meal.macros.calories,
            'protein': meal.macros.protein,
            'carbs': meal.macros.carbs,
            'fat': meal.macros.fat,
          },
        },
      )
      .toList(growable: false);

  return <String, dynamic>{
    if (discoverySessionId != null) 'session_id': discoverySessionId,
    'selected_meal_ids': selected.map((meal) => meal.id).toList(growable: false),
    'selected_meals': selectedMeals,
    'meal_names': mealNames,
    'meal_type': mealType,
    if (calorieTarget != null) 'calorie_target': calorieTarget,
    if (cuisineRegion != null) 'cuisine_region': cuisineRegion,
    if (ingredients.isNotEmpty) 'ingredients': ingredients,
    if (proteinTarget != null) 'protein_target': proteinTarget.toDouble(),
    if (carbsTarget != null) 'carbs_target': carbsTarget.toDouble(),
    if (fatTarget != null) 'fat_target': fatTarget.toDouble(),
  };
}
```

- [ ] **Step 4: Run helper tests and verify pass**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
flutter test test/features/meal_suggestion/application/recipe_request_payload_test.dart
```

Expected: PASS.

- [ ] **Step 5: Commit mobile helper**

```bash
cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
git add lib/features/meal_suggestion/application/utils/recipe_request_payload.dart test/features/meal_suggestion/application/recipe_request_payload_test.dart
git commit -m "test: add selected recipe request payload builder"
```

---

### Task 5: Mobile Provider Uses Full Selected Batch

**Files:**
- Modify: `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/meal_suggestion/application/providers/meal_suggestion_flow_provider.dart`

- [ ] **Step 1: Import the helper**

Add this import to `/Users/alexnguyen/Desktop/Nut/nutree/nutree_ai/lib/features/meal_suggestion/application/providers/meal_suggestion_flow_provider.dart`:

```dart
import 'package:nutree_ai/features/meal_suggestion/application/utils/recipe_request_payload.dart';
```

- [ ] **Step 2: Replace inline request map**

Inside `generateRecipesForSelected`, keep `missing`, `toFetch`, and `nameToId` for cache reconciliation, but replace the inline request map passed to `generateRecipes` with:

```dart
              request: buildSelectedRecipeRequest(
                selected: selected,
                discoverySessionId: state.discoverySessionId,
                mealType: state.mealType ?? _defaultMealType,
                calorieTarget: state.calorieTarget,
                cuisineRegion: state.cuisineRegion,
                ingredients: state.ingredients,
                proteinTarget: state.remainingProtein,
                carbsTarget: state.remainingCarbs,
                fatTarget: state.remainingFat,
              ),
```

The loop still computes `missing` to decide whether an API call is needed. The API call sends the full `selected` list to keep the backend strict selected contract.

- [ ] **Step 3: Run targeted mobile tests**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
flutter test test/features/meal_suggestion/application/recipe_request_payload_test.dart test/features/meal_suggestion/application/recipe_reconciliation_test.dart
```

Expected: PASS.

- [ ] **Step 4: Run static analysis for changed mobile files**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
HOME=/private/tmp DART_SUPPRESS_ANALYTICS=true flutter analyze lib/features/meal_suggestion/application/providers/meal_suggestion_flow_provider.dart lib/features/meal_suggestion/application/utils/recipe_request_payload.dart
```

Expected: PASS with no new errors for these files.

- [ ] **Step 5: Commit mobile provider change**

```bash
cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
git add lib/features/meal_suggestion/application/providers/meal_suggestion_flow_provider.dart
git commit -m "fix: send selected meals for recipe generation"
```

---

### Task 6: Final Verification

**Files:**
- Verify backend and mobile changed files.

- [ ] **Step 1: Run backend focused test suite**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
pytest tests/unit/infra/services/ai/test_schemas.py tests/unit/domain/services/test_suggestion_prompt_builder.py tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_order.py tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py tests/unit/api/test_meal_suggestions_routes.py -q
```

Expected: PASS.

- [ ] **Step 2: Run backend broader meal suggestion unit tests**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
pytest tests/unit/domain/services/meal_suggestion tests/unit/domain/services/test_suggestion_orchestration_service.py tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py tests/unit/api/test_meal_suggestions_routes.py -q
```

Expected: PASS.

- [ ] **Step 3: Run mobile focused tests**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
flutter test test/features/meal_suggestion/application/recipe_request_payload_test.dart test/features/meal_suggestion/application/recipe_reconciliation_test.dart
```

Expected: PASS.

- [ ] **Step 4: Run mobile focused analysis**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
HOME=/private/tmp DART_SUPPRESS_ANALYTICS=true flutter analyze lib/features/meal_suggestion/application/providers/meal_suggestion_flow_provider.dart lib/features/meal_suggestion/application/utils/recipe_request_payload.dart
```

Expected: PASS with no new errors for these files.

- [ ] **Step 5: Inspect git status in both repos**

Run:

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
git status --short
cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
git status --short
```

Expected: backend only has intended commits. Mobile may still show pre-existing unrelated dirty files:

```text
 M lib/features/onboarding/presentation/screens/notification_ask_screen.dart
 M lib/features/onboarding/presentation/screens/pre_att_screen.dart
 M lib/features/subscriptions/application/providers/paywall_variant_provider.dart
```

Do not revert those unrelated mobile changes.

- [ ] **Step 6: Final commit if verification fixes were needed**

If verification required small follow-up changes, commit only those touched files:

```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
git add <verified-backend-files>
git commit -m "fix: stabilize selected recipe verification"

cd /Users/alexnguyen/Desktop/Nut/nutree/nutree_ai
git add <verified-mobile-files>
git commit -m "fix: stabilize selected recipe request payload"
```

If no follow-up changes were needed, skip this commit step.

---

## Self-Review Notes

Spec coverage:

- Mobile rich payload: Task 4 and Task 5.
- Backend strict all-or-nothing: Task 1 and Task 3.
- Structured output contract: Task 2 and Task 3.
- Prompt wording cleanup: Task 2 and Task 3.
- Controlled retryable errors: Task 1 and Task 3.
- Tests and verification: Task 1, Task 2, Task 4, Task 5, and Task 6.

No separate async job plan is included because the approved spec lists async jobs and polling