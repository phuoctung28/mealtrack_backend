# Meal Image Analyze Parallel Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `/v1/meals/image/analyze` latency by running AI analysis and image upload concurrently while keeping image-required semantics.

**Architecture:** Keep existing API contract and handler entrypoint, but refactor `UploadMealImageImmediatelyHandler.handle()` to execute two independent operations in parallel (AI analysis + Cloudinary upload). Gate new behavior behind a feature flag to allow safe canary rollout, and enforce deterministic failure matrix behavior so READY meals always have persisted images.

**Tech Stack:** Python 3.11, FastAPI, asyncio, pytest, existing CQRS/event-bus handler architecture.

---

### Task 1: Add policy/config support for parallel upload mode

**Files:**
- Modify: `src/infra/config/settings.py`
- Modify: `src/domain/services/meal_analysis/fast_path_policy.py`
- Test: `tests/unit/domain/services/meal_analysis/test_fast_path_policy.py`

- [ ] **Step 1: Write the failing test**

```python
def test_from_settings_reads_parallel_upload_flag():
    from types import SimpleNamespace
    from src.domain.services.meal_analysis.fast_path_policy import MealAnalyzeFastPathPolicy

    settings = SimpleNamespace(
        MEAL_ANALYZE_PRIMARY_TIMEOUT_SECONDS=2.5,
        MEAL_ANALYZE_RETRY_TIMEOUT_SECONDS=1.5,
        MEAL_ANALYZE_MAX_ATTEMPTS=2,
        MEAL_ANALYZE_MAX_OUTPUT_TOKENS=700,
        MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH=False,
        MEAL_ANALYZE_RUNTIME_POLICY_ENABLED=True,
        MEAL_ANALYZE_CANARY_PERCENT=100,
        MEAL_ANALYZE_PARALLEL_UPLOAD_ENABLED=True,
    )

    policy = MealAnalyzeFastPathPolicy.from_settings(settings)
    assert policy.parallel_upload_enabled is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/services/meal_analysis/test_fast_path_policy.py::test_from_settings_reads_parallel_upload_flag -v`
Expected: FAIL because `parallel_upload_enabled` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# src/infra/config/settings.py
MEAL_ANALYZE_PARALLEL_UPLOAD_ENABLED: bool = Field(default=False)

# src/domain/services/meal_analysis/fast_path_policy.py (dataclass)
parallel_upload_enabled: bool = False

# src/domain/services/meal_analysis/fast_path_policy.py (legacy)
parallel_upload_enabled=False,

# src/domain/services/meal_analysis/fast_path_policy.py (from_settings)
parallel_upload_enabled=settings.MEAL_ANALYZE_PARALLEL_UPLOAD_ENABLED,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/services/meal_analysis/test_fast_path_policy.py::test_from_settings_reads_parallel_upload_flag -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/infra/config/settings.py src/domain/services/meal_analysis/fast_path_policy.py tests/unit/domain/services/meal_analysis/test_fast_path_policy.py
git commit -m "feat(meal-analyze): add parallel upload policy flag"
```

### Task 2: Add failing handler tests for parallel behavior and failure matrix

**Files:**
- Modify: `tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py`
- Reference implementation target: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.asyncio
async def test_parallel_mode_runs_upload_and_analysis_and_returns_ready():
    handler, saved_state = _make_handler(parallel_upload_enabled=True)
    handler.image_store.save.return_value = "https://cloudinary/meal.jpg"
    handler.vision_service.analyze.return_value = {"structured_data": {"foods": [{"name": "Rice", "quantity": 1, "unit": "serving", "macros": {"protein": 4, "carbs": 40, "fat": 1}}]}}
    command = UploadMealImageImmediatelyCommand(user_id="00000000-0000-0000-0000-000000000001", file_contents=b"img", content_type="image/jpeg")

    meal = await handler.handle(command)

    assert meal.status.value == "READY"
    assert meal.image is not None
    assert meal.image.url == "https://cloudinary/meal.jpg"

@pytest.mark.asyncio
async def test_parallel_mode_marks_failed_when_upload_fails_but_analysis_succeeds():
    handler, saved_state = _make_handler(parallel_upload_enabled=True)
    handler.image_store.save.side_effect = Exception("upload failed")
    handler.vision_service.analyze.return_value = {"structured_data": {"foods": [{"name": "Rice", "quantity": 1, "unit": "serving", "macros": {"protein": 4, "carbs": 40, "fat": 1}}]}}
    command = UploadMealImageImmediatelyCommand(user_id="00000000-0000-0000-0000-000000000001", file_contents=b"img", content_type="image/jpeg")

    with pytest.raises(RuntimeError, match="Image upload failed"):
        await handler.handle(command)

    assert saved_state["meal"].status.value == "FAILED"

@pytest.mark.asyncio
async def test_parallel_mode_marks_failed_when_analysis_fails_even_if_upload_succeeds():
    handler, saved_state = _make_handler(parallel_upload_enabled=True)
    handler.image_store.save.return_value = "https://cloudinary/meal.jpg"
    handler.vision_service.analyze.return_value = {"structured_data": {"foods": []}}
    command = UploadMealImageImmediatelyCommand(user_id="00000000-0000-0000-0000-000000000001", file_contents=b"img", content_type="image/jpeg")

    with pytest.raises(ValueError, match="No edible food detected"):
        await handler.handle(command)

    assert saved_state["meal"].status.value == "FAILED"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py -v`
Expected: FAIL in new tests because handler still executes sequential path.

- [ ] **Step 3: Add minimal test fixtures/helpers needed for deterministic assertions**

```python
saved_state = {}

async def save_meal(meal):
    saved_state["meal"] = meal
    return meal

async def find_meal(meal_id, projection=None):
    return saved_state["meal"]
```

- [ ] **Step 4: Re-run to keep RED**

Run: `pytest tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py::test_parallel_mode_runs_upload_and_analysis_and_returns_ready -v`
Expected: still FAIL (feature not implemented yet).

- [ ] **Step 5: Commit test-only RED state**

```bash
git add tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py
git commit -m "test(meal-analyze): add parallel upload behavior regression tests"
```

### Task 3: Implement parallel handler execution behind flag

**Files:**
- Modify: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Modify: `src/domain/services/meal_analysis/fast_path_policy.py`
- Test: `tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py`

- [ ] **Step 1: Implement parallel branch in handler**

```python
import asyncio

if resolved_policy.parallel_upload_enabled:
    upload_task = asyncio.create_task(
        asyncio.to_thread(self.image_store.save, command.file_contents, command.content_type)
    )
    analysis_task = asyncio.create_task(
        asyncio.to_thread(self._run_vision_analysis, command, saved_meal.meal_id)
    )
    upload_result, analysis_result = await asyncio.gather(
        upload_task, analysis_task, return_exceptions=True
    )
```

- [ ] **Step 2: Implement failure matrix and image-required semantics**

```python
if isinstance(upload_result, Exception) and not isinstance(analysis_result, Exception):
    raise RuntimeError(f"Image upload failed: {upload_result}")

if isinstance(analysis_result, Exception):
    if not isinstance(upload_result, Exception):
        # best-effort cleanup, do not swallow analysis error
        self.image_store.delete(extracted_image_id)
    raise analysis_result
```

- [ ] **Step 3: Keep sequential fallback when feature flag disabled**

```python
if not resolved_policy.parallel_upload_enabled:
    image_url = self.image_store.save(command.file_contents, command.content_type)
    vision_result = self._run_vision_analysis(command, saved_meal.meal_id)
```

- [ ] **Step 4: Ensure logging includes per-phase timings for new path**

```python
logger.info(f"[PHASE-UPLOAD-START] meal={saved_meal.meal_id}")
logger.info(f"[PHASE-UPLOAD-COMPLETE] meal={saved_meal.meal_id} elapsed={upload_elapsed:.2f}s")
logger.warning(f"[PHASE-UPLOAD-FAIL] meal={saved_meal.meal_id} error={upload_error}")
```

- [ ] **Step 5: Run focused tests**

Run: `pytest tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py -v`
Expected: PASS for new parallel behavior tests and existing fast-path tests.

- [ ] **Step 6: Commit implementation**

```bash
git add src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py src/domain/services/meal_analysis/fast_path_policy.py tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py
git commit -m "feat(meal-analyze): run upload and analysis in parallel"
```

### Task 4: Verify route contract compatibility and canary-safe rollout

**Files:**
- Modify: `tests/integration/api/test_meals_api.py`
- Modify: `src/api/routes/v1/meals.py`
- Modify: `src/infra/config/settings.py`

- [ ] **Step 1: Write integration regression tests for error mapping**

```python
def test_analyze_meal_image_returns_not_food_error_when_analysis_rejects(authenticated_client, monkeypatch):
    monkeypatch.setenv("MEAL_ANALYZE_PARALLEL_UPLOAD_ENABLED", "1")
    files = {"file": ("meal.jpg", b"fake-bytes", "image/jpeg")}
    response = authenticated_client.post("/v1/meals/image/analyze", files=files)
    assert response.status_code in (400, 422)
    assert "Could not identify food" in response.text

def test_analyze_meal_image_returns_failure_when_upload_fails(authenticated_client, monkeypatch):
    monkeypatch.setenv("MEAL_ANALYZE_PARALLEL_UPLOAD_ENABLED", "1")
    files = {"file": ("meal.jpg", b"fake-bytes", "image/jpeg")}
    response = authenticated_client.post("/v1/meals/image/analyze", files=files)
    assert response.status_code >= 400
```

- [ ] **Step 2: Run integration tests to verify current behavior**

Run: `pytest tests/integration/api/test_meals_api.py -k "analyze_meal_image" -v`
Expected: PASS for success scenarios and expected error shapes in failure scenarios.

- [ ] **Step 3: Run lint/type checks for touched files**

Run: `black src/ tests/ && flake8 src/ && mypy src/`
Expected: no formatting/lint/type errors.

- [ ] **Step 4: Run targeted + full tests for confidence**

Run: `pytest tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py tests/unit/domain/services/meal_analysis/test_fast_path_policy.py tests/integration/api/test_meals_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit rollout-safe verification updates**

```bash
git add tests/integration/api/test_meals_api.py src/api/routes/v1/meals.py src/infra/config/settings.py
git commit -m "test(meal-analyze): verify parallel upload path contract"
```

### Task 5: Final validation and release notes for operators

**Files:**
- Modify: `README.md` or `docs/troubleshooting.md` (whichever currently documents runtime env flags)

- [ ] **Step 1: Document new flag and rollout guidance**

```markdown
MEAL_ANALYZE_PARALLEL_UPLOAD_ENABLED=false  # default
# enable gradually after canary metrics are healthy
```

- [ ] **Step 2: Run docs-adjacent verification command**

Run: `pytest tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py -v`
Expected: PASS (no behavior regressions after docs touch).

- [ ] **Step 3: Commit documentation**

```bash
git add README.md docs/troubleshooting.md
git commit -m "docs(meal-analyze): add parallel upload rollout notes"
```
