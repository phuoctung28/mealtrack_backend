# Gemini Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Handle Gemini API rate limits and model unavailability with coordinated throttling, retry logic, and proper HTTP 503 responses.

**Architecture:** New `GeminiThrottle` singleton coordinates all Gemini calls via semaphore (max 4 concurrent) + cooldown timestamp. Callers acquire throttle before `asyncio.to_thread()`. `MealGenerationService` detects rate limit errors and retries once with 1s backoff.

**Tech Stack:** Python asyncio (Semaphore, Lock), google-api-core exceptions, FastAPI exception handlers

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/infra/services/ai/gemini_throttle.py` | **New** — Singleton throttle with semaphore + cooldown |
| `src/infra/adapters/meal_generation_service.py` | **Modify** — Add error detection, retry logic, raise ExternalServiceException |
| `src/domain/services/meal_suggestion/recipe_attempt_builder.py` | **Modify** — Wrap calls with throttle.acquire() |
| `src/domain/services/meal_suggestion/parallel_recipe_generator.py` | **Modify** — Wrap Phase 1 and Discovery calls with throttle |
| `src/api/main.py` | **Modify** — Add ExternalServiceException handler with Retry-After header |
| `tests/unit/infra/services/ai/test_gemini_throttle.py` | **New** — Unit tests for throttle |
| `tests/unit/infra/adapters/test_meal_generation_resilience.py` | **New** — Unit tests for error detection |
| `tests/integration/test_gemini_rate_limit_handling.py` | **New** — Integration test for full flow |

---

## Task 1: Create GeminiThrottle Singleton

**Files:**
- Create: `src/infra/services/ai/gemini_throttle.py`
- Test: `tests/unit/infra/services/ai/test_gemini_throttle.py`

- [ ] **Step 1: Create test directory structure**

```bash
mkdir -p tests/unit/infra/services/ai
touch tests/unit/infra/services/ai/__init__.py
```

- [ ] **Step 2: Write failing test for singleton**

Create `tests/unit/infra/services/ai/test_gemini_throttle.py`:

```python
"""Unit tests for GeminiThrottle."""
import pytest


class TestGeminiThrottleSingleton:
    """Tests for singleton behavior."""

    def test_get_instance_returns_same_object(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        instance1 = GeminiThrottle.get_instance()
        instance2 = GeminiThrottle.get_instance()

        assert instance1 is instance2

    def test_reset_clears_instance(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        instance1 = GeminiThrottle.get_instance()
        GeminiThrottle.reset()
        instance2 = GeminiThrottle.get_instance()

        assert instance1 is not instance2
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/infra/services/ai/test_gemini_throttle.py -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

- [ ] **Step 4: Write minimal GeminiThrottle implementation**

Create `src/infra/services/ai/gemini_throttle.py`:

```python
"""
Gemini API throttle for rate limit management.
Coordinates all Gemini calls via semaphore + cooldown.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONCURRENT = 4
DEFAULT_COOLDOWN_SECONDS = 3


class GeminiThrottle:
    """
    Singleton throttle for Gemini API calls.
    
    - Semaphore limits concurrent calls (default: 4)
    - Cooldown blocks all calls briefly after rate limit detected
    """

    _instance: Optional["GeminiThrottle"] = None

    def __init__(self, max_concurrent: int = DEFAULT_MAX_CONCURRENT):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cooldown_until: float = 0
        self._lock = asyncio.Lock()
        self._max_concurrent = max_concurrent

    @classmethod
    def get_instance(cls, max_concurrent: int = DEFAULT_MAX_CONCURRENT) -> "GeminiThrottle":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls(max_concurrent)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/infra/services/ai/test_gemini_throttle.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/infra/services/ai/gemini_throttle.py tests/unit/infra/services/ai/
git commit -m "feat(ai): add GeminiThrottle singleton skeleton

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Add Semaphore Concurrency Limiting

**Files:**
- Modify: `src/infra/services/ai/gemini_throttle.py`
- Modify: `tests/unit/infra/services/ai/test_gemini_throttle.py`

- [ ] **Step 1: Write failing test for semaphore limiting**

Add to `tests/unit/infra/services/ai/test_gemini_throttle.py`:

```python
import asyncio


class TestGeminiThrottleSemaphore:
    """Tests for semaphore concurrency limiting."""

    @pytest.fixture(autouse=True)
    def reset_throttle(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle
        GeminiThrottle.reset()
        yield
        GeminiThrottle.reset()

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        throttle = GeminiThrottle.get_instance(max_concurrent=2)
        active_count = 0
        max_observed = 0
        results = []

        async def task(task_id: int):
            nonlocal active_count, max_observed
            async with throttle.acquire():
                active_count += 1
                max_observed = max(max_observed, active_count)
                await asyncio.sleep(0.1)
                active_count -= 1
                results.append(task_id)

        await asyncio.gather(*[task(i) for i in range(6)])

        assert max_observed <= 2, f"Expected max 2 concurrent, got {max_observed}"
        assert len(results) == 6, "All tasks should complete"

    @pytest.mark.asyncio
    async def test_acquire_releases_on_exception(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        throttle = GeminiThrottle.get_instance(max_concurrent=1)

        with pytest.raises(ValueError):
            async with throttle.acquire():
                raise ValueError("test error")

        # Should be able to acquire again
        async with throttle.acquire():
            pass  # Success if we get here
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infra/services/ai/test_gemini_throttle.py::TestGeminiThrottleSemaphore -v`
Expected: FAIL with "AttributeError: 'GeminiThrottle' object has no attribute 'acquire'"

- [ ] **Step 3: Implement acquire() method**

Add to `src/infra/services/ai/gemini_throttle.py` in the `GeminiThrottle` class:

```python
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        """
        Acquire throttle before making Gemini API call.
        
        Waits for:
        1. Cooldown to expire (if active)
        2. Semaphore slot to become available
        """
        # Wait for cooldown if active
        async with self._lock:
            wait_time = self._cooldown_until - time.time()
        
        if wait_time > 0:
            logger.info(f"[THROTTLE] Waiting {wait_time:.2f}s for cooldown")
            await asyncio.sleep(wait_time)

        # Acquire semaphore
        async with self._semaphore:
            yield
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infra/services/ai/test_gemini_throttle.py::TestGeminiThrottleSemaphore -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/services/ai/gemini_throttle.py tests/unit/infra/services/ai/test_gemini_throttle.py
git commit -m "feat(ai): add semaphore concurrency limiting to GeminiThrottle

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Add Cooldown Mechanism

**Files:**
- Modify: `src/infra/services/ai/gemini_throttle.py`
- Modify: `tests/unit/infra/services/ai/test_gemini_throttle.py`

- [ ] **Step 1: Write failing test for cooldown**

Add to `tests/unit/infra/services/ai/test_gemini_throttle.py`:

```python
class TestGeminiThrottleCooldown:
    """Tests for cooldown mechanism."""

    @pytest.fixture(autouse=True)
    def reset_throttle(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle
        GeminiThrottle.reset()
        yield
        GeminiThrottle.reset()

    @pytest.mark.asyncio
    async def test_record_rate_limit_sets_cooldown(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        throttle = GeminiThrottle.get_instance()
        
        assert not throttle.is_in_cooldown()
        
        throttle.record_rate_limit(retry_after=2)
        
        assert throttle.is_in_cooldown()

    @pytest.mark.asyncio
    async def test_cooldown_blocks_acquire(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        throttle = GeminiThrottle.get_instance()
        throttle.record_rate_limit(retry_after=1)

        start = time.time()
        async with throttle.acquire():
            elapsed = time.time() - start

        assert elapsed >= 0.9, f"Should wait ~1s, waited {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_cooldown_expires(self):
        from src.infra.services.ai.gemini_throttle import GeminiThrottle

        throttle = GeminiThrottle.get_instance()
        throttle.record_rate_limit(retry_after=1)
        
        await asyncio.sleep(1.1)
        
        assert not throttle.is_in_cooldown()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infra/services/ai/test_gemini_throttle.py::TestGeminiThrottleCooldown -v`
Expected: FAIL with "AttributeError: 'GeminiThrottle' object has no attribute 'record_rate_limit'"

- [ ] **Step 3: Implement cooldown methods**

Add to `src/infra/services/ai/gemini_throttle.py` in the `GeminiThrottle` class:

```python
    def record_rate_limit(self, retry_after: int = DEFAULT_COOLDOWN_SECONDS) -> None:
        """
        Record that a rate limit was hit.
        Sets cooldown to block new requests briefly.
        """
        new_cooldown = time.time() + retry_after
        if new_cooldown > self._cooldown_until:
            self._cooldown_until = new_cooldown
            logger.warning(
                f"[THROTTLE] Rate limit hit, cooldown for {retry_after}s"
            )

    def is_in_cooldown(self) -> bool:
        """Check if currently in cooldown period."""
        return time.time() < self._cooldown_until

    def get_cooldown_remaining(self) -> float:
        """Get seconds remaining in cooldown, or 0 if not in cooldown."""
        remaining = self._cooldown_until - time.time()
        return max(0, remaining)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infra/services/ai/test_gemini_throttle.py::TestGeminiThrottleCooldown -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/services/ai/gemini_throttle.py tests/unit/infra/services/ai/test_gemini_throttle.py
git commit -m "feat(ai): add cooldown mechanism to GeminiThrottle

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Add Rate Limit Error Detection Helper

**Files:**
- Create: `src/infra/services/ai/gemini_error_utils.py`
- Test: `tests/unit/infra/services/ai/test_gemini_error_utils.py`

- [ ] **Step 1: Write failing tests for error detection**

Create `tests/unit/infra/services/ai/test_gemini_error_utils.py`:

```python
"""Unit tests for Gemini error detection utilities."""
import pytest


class TestIsRateLimitError:
    """Tests for is_rate_limit_error function."""

    def test_detects_429_in_message(self):
        from src.infra.services.ai.gemini_error_utils import is_rate_limit_error

        error = Exception("Error 429: Too Many Requests")
        assert is_rate_limit_error(error) is True

    def test_detects_resource_exhausted(self):
        from src.infra.services.ai.gemini_error_utils import is_rate_limit_error

        error = Exception("ResourceExhausted: quota exceeded")
        assert is_rate_limit_error(error) is True

    def test_detects_503_overloaded(self):
        from src.infra.services.ai.gemini_error_utils import is_rate_limit_error

        error = Exception("503 Service Unavailable: model overloaded")
        assert is_rate_limit_error(error) is True

    def test_detects_quota_keyword(self):
        from src.infra.services.ai.gemini_error_utils import is_rate_limit_error

        error = Exception("Quota limit reached for this API")
        assert is_rate_limit_error(error) is True

    def test_ignores_unrelated_errors(self):
        from src.infra.services.ai.gemini_error_utils import is_rate_limit_error

        error = ValueError("Invalid input format")
        assert is_rate_limit_error(error) is False

    def test_handles_resource_exhausted_exception_type(self):
        from src.infra.services.ai.gemini_error_utils import is_rate_limit_error
        from google.api_core.exceptions import ResourceExhausted

        error = ResourceExhausted("Quota exceeded")
        assert is_rate_limit_error(error) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infra/services/ai/test_gemini_error_utils.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement error detection helper**

Create `src/infra/services/ai/gemini_error_utils.py`:

```python
"""
Utilities for detecting and handling Gemini API errors.
"""
from typing import Tuple

try:
    from google.api_core.exceptions import ResourceExhausted
    HAS_GOOGLE_API_CORE = True
except ImportError:
    HAS_GOOGLE_API_CORE = False
    ResourceExhausted = None

RATE_LIMIT_INDICATORS = (
    "429",
    "resource exhausted",
    "resourceexhausted",
    "503",
    "overloaded",
    "quota",
    "rate limit",
    "too many requests",
)


def is_rate_limit_error(error: Exception) -> bool:
    """
    Check if an exception indicates a rate limit or quota error.
    
    Detects:
    - google.api_core.exceptions.ResourceExhausted
    - HTTP 429 errors wrapped in exceptions
    - HTTP 503 "overloaded" errors
    - Any exception message containing quota/rate limit keywords
    """
    # Check exception type first
    if HAS_GOOGLE_API_CORE and ResourceExhausted is not None:
        if isinstance(error, ResourceExhausted):
            return True

    # Check exception message
    error_str = str(error).lower()
    return any(indicator in error_str for indicator in RATE_LIMIT_INDICATORS)


def get_retry_after_from_error(error: Exception) -> int:
    """
    Extract retry-after value from error, or return default.
    
    Returns:
        Seconds to wait before retrying (default: 3)
    """
    error_str = str(error).lower()
    
    # Check for 503 (model overload) - shorter wait
    if "503" in error_str or "overloaded" in error_str:
        return 2
    
    # Default for rate limits
    return 3
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infra/services/ai/test_gemini_error_utils.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/services/ai/gemini_error_utils.py tests/unit/infra/services/ai/test_gemini_error_utils.py
git commit -m "feat(ai): add rate limit error detection utilities

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Add Retry Logic to MealGenerationService

**Files:**
- Modify: `src/infra/adapters/meal_generation_service.py`
- Test: `tests/unit/infra/adapters/test_meal_generation_resilience.py`

- [ ] **Step 1: Create test file with failing test**

Create `tests/unit/infra/adapters/test_meal_generation_resilience.py`:

```python
"""Unit tests for MealGenerationService rate limit handling."""
import pytest
from unittest.mock import MagicMock, patch

from src.api.exceptions import ExternalServiceException


class TestMealGenerationServiceResilience:
    """Tests for rate limit retry logic."""

    @pytest.fixture
    def mock_model_manager(self):
        manager = MagicMock()
        manager.model_name = "gemini-test"
        mock_llm = MagicMock()
        manager.get_model_for_purpose.return_value = mock_llm
        manager.get_model.return_value = mock_llm
        return manager

    @pytest.fixture
    def service(self, mock_model_manager):
        from src.infra.adapters.meal_generation_service import MealGenerationService
        
        with patch.object(
            MealGenerationService, '__init__', lambda self: None
        ):
            svc = MealGenerationService()
            svc._model_manager = mock_model_manager
            return svc

    def test_retries_once_on_resource_exhausted(self, service, mock_model_manager):
        from google.api_core.exceptions import ResourceExhausted

        mock_llm = mock_model_manager.get_model_for_purpose.return_value
        
        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.content = '{"meal_name": "Test Meal"}'
        mock_llm.invoke.side_effect = [
            ResourceExhausted("Quota exceeded"),
            mock_response,
        ]

        result = service.generate_meal_plan(
            prompt="test prompt",
            system_message="test system",
            response_type="json",
        )

        assert mock_llm.invoke.call_count == 2
        assert result == {"meal_name": "Test Meal"}

    def test_raises_external_service_exception_after_retry_fails(
        self, service, mock_model_manager
    ):
        from google.api_core.exceptions import ResourceExhausted

        mock_llm = mock_model_manager.get_model_for_purpose.return_value
        mock_llm.invoke.side_effect = ResourceExhausted("Quota exceeded")

        with pytest.raises(ExternalServiceException) as exc_info:
            service.generate_meal_plan(
                prompt="test prompt",
                system_message="test system",
                response_type="json",
            )

        assert exc_info.value.error_code == "AI_RATE_LIMITED"
        assert exc_info.value.details["retry_after_seconds"] == 5
        assert mock_llm.invoke.call_count == 2

    def test_non_rate_limit_error_propagates_immediately(
        self, service, mock_model_manager
    ):
        mock_llm = mock_model_manager.get_model_for_purpose.return_value
        mock_llm.invoke.side_effect = ValueError("Invalid input")

        with pytest.raises(ValueError, match="Invalid input"):
            service.generate_meal_plan(
                prompt="test prompt",
                system_message="test system",
                response_type="json",
            )

        assert mock_llm.invoke.call_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infra/adapters/test_meal_generation_resilience.py -v`
Expected: FAIL (no retry logic implemented yet)

- [ ] **Step 3: Add retry logic to generate_meal_plan**

Modify `src/infra/adapters/meal_generation_service.py`. Add import at top:

```python
import time

from src.api.exceptions import ExternalServiceException
from src.infra.services.ai.gemini_error_utils import is_rate_limit_error

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    ResourceExhausted = None
```

Then modify the `generate_meal_plan` method. Find the try/except block around line 240 and replace it:

```python
        max_attempts = 2
        last_error = None

        for attempt in range(max_attempts):
            try:
                # ... existing LLM call logic stays here ...
                # (the code between "try:" and "except Exception as e:")
                
            except Exception as e:
                last_error = e
                elapsed = time.time() - start_time
                
                # Check if this is a rate limit error
                is_rate_limit = (
                    (ResourceExhausted is not None and isinstance(e, ResourceExhausted))
                    or is_rate_limit_error(e)
                )
                
                if is_rate_limit and attempt < max_attempts - 1:
                    logger.warning(
                        f"[AI-RATE-LIMIT] attempt={attempt + 1} | "
                        f"elapsed={elapsed:.2f}s | "
                        f"error_type={type(e).__name__} | "
                        f"retrying in 1s"
                    )
                    time.sleep(1)
                    continue
                
                if is_rate_limit:
                    logger.error(
                        f"[AI-RATE-LIMIT-EXHAUSTED] attempts={max_attempts} | "
                        f"elapsed={elapsed:.2f}s | "
                        f"error_type={type(e).__name__}"
                    )
                    raise ExternalServiceException(
                        message="AI service temporarily unavailable",
                        error_code="AI_RATE_LIMITED",
                        details={
                            "retry_after_seconds": 5,
                            "reason": "rate_limit",
                        }
                    )
                
                logger.error(
                    f"[AI-ERROR] elapsed={elapsed:.2f}s | "
                    f"error_type={type(e).__name__} | "
                    f"error={str(e)[:200]}"
                )
                raise
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infra/adapters/test_meal_generation_resilience.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/adapters/meal_generation_service.py tests/unit/infra/adapters/test_meal_generation_resilience.py
git commit -m "feat(ai): add retry logic for rate limit errors in MealGenerationService

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Add Throttle to Recipe Attempt Builder

**Files:**
- Modify: `src/domain/services/meal_suggestion/recipe_attempt_builder.py`

- [ ] **Step 1: Read current implementation**

Review `src/domain/services/meal_suggestion/recipe_attempt_builder.py` to understand the current structure.

- [ ] **Step 2: Add throttle import and usage**

Add import at top of file:

```python
from src.infra.services.ai.gemini_throttle import GeminiThrottle
from src.api.exceptions import ExternalServiceException
```

Modify the `attempt_recipe_generation` function. Wrap the existing try block with throttle:

```python
async def attempt_recipe_generation(
    generation_service: MealGenerationServicePort,
    macro_validator: MacroValidationService,
    nutrition_lookup: NutritionLookupService,
    prompt: str,
    meal_name: str,
    index: int,
    model_purpose: str,
    recipe_system: str,
    session: SuggestionSession,
    is_retry: bool = False,
) -> Optional[MealSuggestion]:
    """
    Single AI call to generate one recipe. Returns MealSuggestion on success, None on failure.
    ... (keep existing docstring)
    """
    marker = "[RETRY]" if is_retry else ""
    throttle = GeminiThrottle.get_instance()
    
    try:
        async with throttle.acquire():
            raw = await asyncio.wait_for(
                asyncio.to_thread(
                    generation_service.generate_meal_plan,
                    prompt,
                    recipe_system,
                    "json",
                    PARALLEL_SINGLE_MEAL_TOKENS,
                    None,
                    model_purpose,
                ),
                timeout=PARALLEL_SINGLE_MEAL_TIMEOUT,
            )
        
        # ... rest of existing success logic (ingredients, recipe_steps, etc.)
        
    except ExternalServiceException:
        # Rate limit after retry in MealGenerationService - record cooldown
        throttle.record_rate_limit(retry_after=3)
        logger.warning(
            f"[PHASE-2-RATE-LIMIT]{marker} index={index} | "
            f"model_purpose={model_purpose} | meal_name={meal_name}"
        )
        return None
    except asyncio.TimeoutError:
        logger.warning(
            f"[PHASE-2-TIMEOUT]{marker} index={index} | "
            f"model_purpose={model_purpose} | meal_name={meal_name}"
        )
        return None
    except Exception as e:
        logger.warning(
            f"[PHASE-2-FAIL]{marker} index={index} | "
            f"model_purpose={model_purpose} | error_type={type(e).__name__} | error={e}"
        )
        return None
```

- [ ] **Step 3: Run existing tests**

Run: `pytest tests/ -k "recipe" --ignore=tests/integration -v`
Expected: PASS (existing tests should still work)

- [ ] **Step 4: Commit**

```bash
git add src/domain/services/meal_suggestion/recipe_attempt_builder.py
git commit -m "feat(ai): add throttle to recipe attempt builder

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Add Throttle to Parallel Recipe Generator

**Files:**
- Modify: `src/domain/services/meal_suggestion/parallel_recipe_generator.py`

- [ ] **Step 1: Add throttle import**

Add import at top of file:

```python
from src.infra.services.ai.gemini_throttle import GeminiThrottle
from src.api.exceptions import ExternalServiceException
```

- [ ] **Step 2: Wrap Phase 1 (generate_names) with throttle**

Modify `_phase1_generate_names` method. Find the `asyncio.wait_for` call and wrap it:

```python
    async def _phase1_generate_names(
        self, session: SuggestionSession, exclude_meal_names: List[str], target_lang: str,
        suggestion_count: int = 3,
    ) -> List[str]:
        # ... existing setup code ...
        
        throttle = GeminiThrottle.get_instance()
        
        try:
            for attempt in range(1, max_attempts + 1):
                async with throttle.acquire():
                    names_raw = await asyncio.wait_for(
                        asyncio.to_thread(
                            self._generation.generate_meal_plan,
                            build_meal_names_prompt(session, exclude_meal_names, names_to_generate),
                            names_system, "json", 1000, meal_names_schema, "meal_names",
                        ),
                        timeout=self.PHASE1_TIMEOUT,
                    )
                # ... rest of existing loop logic ...
        except ExternalServiceException:
            throttle.record_rate_limit(retry_after=3)
            logger.error(f"[PHASE-1-RATE-LIMIT] session={session.id}")
            raise RuntimeError("Rate limit exceeded during meal name generation")
        except Exception as e:
            logger.error(f"[PHASE-1-FAILED] session={session.id} | {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to generate meal names: {e}") from e
```

- [ ] **Step 3: Wrap Discovery with throttle**

Modify `generate_discovery` method. Find the `asyncio.wait_for` call and wrap it:

```python
    async def generate_discovery(
        self,
        session: SuggestionSession,
        exclude_meal_names: List[str],
        count: int = 6,
    ) -> List[dict]:
        # ... existing setup code ...
        
        throttle = GeminiThrottle.get_instance()
        
        try:
            async with throttle.acquire():
                raw = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._generation.generate_meal_plan,
                        prompt, system, "json", 1000, discovery_schema, "meal_names",
                    ),
                    timeout=self.DISCOVERY_TIMEOUT,
                )
        except ExternalServiceException:
            throttle.record_rate_limit(retry_after=3)
            logger.error(f"[DISCOVERY-RATE-LIMIT] session={session.id}")
            raise RuntimeError("Rate limit exceeded during discovery")
        except Exception as e:
            logger.error(f"[DISCOVERY-FAILED] session={session.id} | {type(e).__name__}: {e}")
            raise RuntimeError(f"Discovery generation failed: {e}") from e
        
        # ... rest of existing processing code ...
```

- [ ] **Step 4: Run existing tests**

Run: `pytest tests/ -k "parallel or generator" --ignore=tests/integration -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/services/meal_suggestion/parallel_recipe_generator.py
git commit -m "feat(ai): add throttle to parallel recipe generator

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Add ExternalServiceException Handler with Retry-After Header

**Files:**
- Modify: `src/api/main.py`

- [ ] **Step 1: Read current exception handlers**

Review `src/api/main.py` to find existing exception handler registration.

- [ ] **Step 2: Add ExternalServiceException handler**

Add import at top if not present:

```python
from fastapi.responses import JSONResponse
from src.api.exceptions import ExternalServiceException
```

Add the exception handler after other handlers (look for `@app.exception_handler`):

```python
@app.exception_handler(ExternalServiceException)
async def external_service_exception_handler(
    request: Request, exc: ExternalServiceException
) -> JSONResponse:
    """Handle external service failures with Retry-After header."""
    retry_after = exc.details.get("retry_after_seconds", 30)
    
    return JSONResponse(
        status_code=503,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
        headers={"Retry-After": str(retry_after)},
    )
```

- [ ] **Step 3: Run API tests**

Run: `pytest tests/integration -v --ignore=tests/integration/test_gemini_rate_limit_handling.py`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/api/main.py
git commit -m "feat(api): add ExternalServiceException handler with Retry-After header

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Add Integration Test

**Files:**
- Create: `tests/integration/test_gemini_rate_limit_handling.py`

- [ ] **Step 1: Write integration test**

Create `tests/integration/test_gemini_rate_limit_handling.py`:

```python
"""Integration tests for Gemini rate limit handling."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.infra.services.ai.gemini_throttle import GeminiThrottle


class TestGeminiRateLimitIntegration:
    """Integration tests for the full rate limit handling flow."""

    @pytest.fixture(autouse=True)
    def reset_throttle(self):
        GeminiThrottle.reset()
        yield
        GeminiThrottle.reset()

    @pytest.mark.asyncio
    async def test_throttle_limits_concurrent_recipe_generation(self):
        """Verify throttle limits concurrent calls to 4."""
        throttle = GeminiThrottle.get_instance(max_concurrent=4)
        
        call_times = []
        active = 0
        max_active = 0

        async def mock_generate():
            nonlocal active, max_active
            async with throttle.acquire():
                active += 1
                max_active = max(max_active, active)
                await asyncio.sleep(0.05)
                active -= 1
                return {"ingredients": [], "recipe_steps": []}

        # Simulate 7 parallel recipe tasks
        tasks = [asyncio.create_task(mock_generate()) for _ in range(7)]
        await asyncio.gather(*tasks)

        assert max_active <= 4, f"Max concurrent should be 4, got {max_active}"

    @pytest.mark.asyncio
    async def test_rate_limit_triggers_cooldown_for_other_requests(self):
        """Verify that rate limit on one request slows down others."""
        throttle = GeminiThrottle.get_instance(max_concurrent=4)
        
        # Simulate first request hitting rate limit
        throttle.record_rate_limit(retry_after=1)
        
        # Second request should wait for cooldown
        import time
        start = time.time()
        async with throttle.acquire():
            elapsed = time.time() - start
        
        assert elapsed >= 0.9, f"Should wait ~1s, waited {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_graceful_degradation_returns_partial_results(self):
        """Verify partial results returned when some tasks fail."""
        from src.api.exceptions import ExternalServiceException
        
        throttle = GeminiThrottle.get_instance(max_concurrent=4)
        results = []
        
        async def task(task_id: int, should_fail: bool):
            async with throttle.acquire():
                if should_fail:
                    throttle.record_rate_limit(retry_after=1)
                    return None
                return {"id": task_id}
        
        # Simulate 7 tasks, 2 fail
        tasks = [
            asyncio.create_task(task(i, i in [2, 5]))
            for i in range(7)
        ]
        results = await asyncio.gather(*tasks)
        
        successful = [r for r in results if r is not None]
        assert len(successful) == 5, f"Expected 5 successes, got {len(successful)}"
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/integration/test_gemini_rate_limit_handling.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_gemini_rate_limit_handling.py
git commit -m "test: add integration tests for Gemini rate limit handling

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Run Full Test Suite and Verify

**Files:** None (verification only)

- [ ] **Step 1: Run all unit tests**

Run: `pytest tests/unit -v`
Expected: All PASS

- [ ] **Step 2: Run all integration tests**

Run: `pytest tests/integration -v`
Expected: All PASS

- [ ] **Step 3: Run type checking**

Run: `mypy src/infra/services/ai/ src/infra/adapters/meal_generation_service.py`
Expected: No errors

- [ ] **Step 4: Run linting**

Run: `flake8 src/infra/services/ai/ src/infra/adapters/meal_generation_service.py`
Expected: No errors

- [ ] **Step 5: Final commit with all changes verified**

```bash
git log --oneline -10
```

Expected: 9 commits for this feature

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | GeminiThrottle singleton skeleton | gemini_throttle.py |
| 2 | Semaphore concurrency limiting | gemini_throttle.py |
| 3 | Cooldown mechanism | gemini_throttle.py |
| 4 | Error detection utilities | gemini_error_utils.py |
| 5 | Retry logic in MealGenerationService | meal_generation_service.py |
| 6 | Throttle in recipe_attempt_builder | recipe_attempt_builder.py |
| 7 | Throttle in parallel_recipe_generator | parallel_recipe_generator.py |
| 8 | ExternalServiceException handler | main.py |
| 9 | Integration test | test_gemini_rate_limit_handling.py |
| 10 | Full verification | (none) |
