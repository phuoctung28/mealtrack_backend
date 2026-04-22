# Vision Latency Reduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut meal image analysis from 14.67s (variable) to under 6s (consistent) by disabling Gemini thinking tokens and compressing images before upload.

**Architecture:** All changes confined to `src/infra/adapters/vision_ai_service.py`. Two independent improvements: (1) model construction params — disable thinking, cap output; (2) image preprocessing — resize + recompress before base64 encode. Every other method that takes `image_bytes` already funnels through `analyze_with_strategy`, so compression only needs to be wired in one place.

**Tech Stack:** Python 3.11+, Pillow (already in `requirements.txt`), LangChain Google GenAI

---

### Task 1: Disable thinking tokens and cap output tokens

**Files:**
- Modify: `src/infra/adapters/vision_ai_service.py:33`
- Create: `tests/unit/infra/adapters/test_vision_ai_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/infra/adapters/test_vision_ai_service.py`:

```python
from unittest.mock import MagicMock, patch

from src.infra.adapters.vision_ai_service import VisionAIService

_MGR_PATCH = "src.infra.adapters.vision_ai_service.GeminiModelManager"


def test_vision_service_disables_thinking_and_caps_output():
    with patch(_MGR_PATCH) as mock_cls:
        mock_mgr = MagicMock()
        mock_cls.get_instance.return_value = mock_mgr

        VisionAIService()

        mock_mgr.get_model.assert_called_once_with(
            thinking_budget=0, max_output_tokens=1024
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/unit/infra/adapters/test_vision_ai_service.py::test_vision_service_disables_thinking_and_caps_output -v
```

Expected: `FAILED — AssertionError: expected call get_model(thinking_budget=0, max_output_tokens=1024), actual call get_model()`

- [ ] **Step 3: Implement — update model construction in `__init__`**

In `src/infra/adapters/vision_ai_service.py`, change line 33:

```python
# Before
self.model = self._model_manager.get_model()

# After
self.model = self._model_manager.get_model(thinking_budget=0, max_output_tokens=1024)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest tests/unit/infra/adapters/test_vision_ai_service.py::test_vision_service_disables_thinking_and_caps_output -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/infra/adapters/vision_ai_service.py tests/unit/infra/adapters/test_vision_ai_service.py
git commit -m "perf(vision): disable thinking tokens and cap output to 1024"
```

---

### Task 2: Add `_compress_image` method

**Files:**
- Modify: `src/infra/adapters/vision_ai_service.py` (add method after `__init__`)
- Modify: `tests/unit/infra/adapters/test_vision_ai_service.py` (add 3 tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/infra/adapters/test_vision_ai_service.py` (add `from io import BytesIO` and `from PIL import Image` to the imports at the top of the file):

```python


def _make_jpeg(width: int, height: int, quality: int = 95) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _make_service() -> VisionAIService:
    """Instantiate VisionAIService without hitting GeminiModelManager."""
    with patch(_MGR_PATCH):
        return VisionAIService()


def test_compress_image_resizes_large_image():
    service = _make_service()
    large_bytes = _make_jpeg(2000, 1500)

    result = service._compress_image(large_bytes)

    img = Image.open(BytesIO(result))
    assert max(img.size) <= 768


def test_compress_image_skips_small_image():
    service = _make_service()
    # Small image: 400x300 at quality 50 will be well under 200KB
    small_bytes = _make_jpeg(400, 300, quality=50)
    assert len(small_bytes) < 200 * 1024  # confirm precondition

    result = service._compress_image(small_bytes)

    # Bytes returned, dimensions unchanged
    img = Image.open(BytesIO(result))
    assert img.size == (400, 300)


def test_compress_image_fallback_on_corrupt_bytes():
    service = _make_service()
    corrupt = b"not an image at all"

    result = service._compress_image(corrupt)

    assert result == corrupt
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/unit/infra/adapters/test_vision_ai_service.py -k "compress" -v
```

Expected: `ERROR — AttributeError: 'VisionAIService' object has no attribute '_compress_image'`

- [ ] **Step 3: Implement `_compress_image`**

In `src/infra/adapters/vision_ai_service.py`, add this method after `__init__` (before `_analyze_image_reference`):

```python
def _compress_image(self, image_bytes: bytes) -> bytes:
    try:
        from io import BytesIO
        from PIL import Image

        img = Image.open(BytesIO(image_bytes))
        w, h = img.size

        if max(w, h) <= 768 and len(image_bytes) < 200 * 1024:
            return image_bytes

        if max(w, h) > 768:
            ratio = 768 / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        if img.mode != "RGB":
            img = img.convert("RGB")

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Image compression failed, using original: %s", exc)
        return image_bytes
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/unit/infra/adapters/test_vision_ai_service.py -k "compress" -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/infra/adapters/vision_ai_service.py tests/unit/infra/adapters/test_vision_ai_service.py
git commit -m "perf(vision): add _compress_image with resize to 768px and quality 85"
```

---

### Task 3: Wire compression into the analysis path

**Files:**
- Modify: `src/infra/adapters/vision_ai_service.py:100`
- Modify: `tests/unit/infra/adapters/test_vision_ai_service.py` (add 1 integration test)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/infra/adapters/test_vision_ai_service.py`:

```python
def test_analyze_with_strategy_compresses_before_encoding():
    service = _make_service()
    service.model = MagicMock()
    service.model.invoke.return_value = MagicMock(
        content='{"dish_name": "test", "ingredients": []}'
    )

    # 2000x1500 image — will be compressed by _compress_image
    large_bytes = _make_jpeg(2000, 1500)

    from src.domain.strategies.meal_analysis_strategy import AnalysisStrategyFactory
    strategy = AnalysisStrategyFactory.create_basic_strategy()

    service.analyze_with_strategy(large_bytes, strategy)

    # Extract the base64 payload that was sent to the model
    call_args = service.model.invoke.call_args[0][0]  # list of messages
    human_msg = call_args[1]
    image_content = human_msg.content[1]["image_url"]["url"]
    assert image_content.startswith("data:image/jpeg;base64,")

    # Decode and check compressed dimensions
    import base64
    encoded = image_content.split(",", 1)[1]
    decoded = base64.b64decode(encoded)
    img = Image.open(BytesIO(decoded))
    assert max(img.size) <= 768
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/unit/infra/adapters/test_vision_ai_service.py::test_analyze_with_strategy_compresses_before_encoding -v
```

Expected: `FAILED — assert max(img.size) <= 768` (image still 2000x1500 because compression not wired in yet)

- [ ] **Step 3: Wire `_compress_image` into `analyze_with_strategy`**

In `src/infra/adapters/vision_ai_service.py`, update `analyze_with_strategy` (lines 100–102):

```python
def analyze_with_strategy(self, image_bytes: bytes, strategy: MealAnalysisStrategy) -> Dict[str, Any]:
    image_bytes = self._compress_image(image_bytes)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_data_url = f"data:image/jpeg;base64,{image_base64}"
    return self._analyze_image_reference(image_data_url, strategy)
```

- [ ] **Step 4: Run all vision service tests**

```bash
.venv/bin/python -m pytest tests/unit/infra/adapters/test_vision_ai_service.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Run full unit suite to check for regressions**

```bash
.venv/bin/python -m pytest tests/unit/ -q
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add src/infra/adapters/vision_ai_service.py tests/unit/infra/adapters/test_vision_ai_service.py
git commit -m "perf(vision): compress image before base64 encode in analyze_with_strategy"
```
