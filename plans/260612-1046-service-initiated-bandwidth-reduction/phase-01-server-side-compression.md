---
phase: 1
title: "Server-Side Compression"
status: pending
priority: P1
effort: "2h"
dependencies: []
---

# Phase 1: Server-Side Compression

## Overview

Extract the existing `_compress_image()` logic from `VisionAIService` into a shared utility, then apply it before the Cloudinary upload in the meal scan handler. Ships with zero mobile changes.

**Expected result:** Cloudinary upload drops from ~5MB to ~400KB per scan (92% reduction in service-initiated outbound bandwidth).

## Context Links

- Design doc: `plans/reports/brainstorm-260612-1046-service-initiated-bandwidth-reduction-report.md`
- Source of `_compress_image`: `src/infra/adapters/vision_ai_service.py:27–52`
- Upload handler: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:115–163`
- Ingredient recognition: `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py`

## Requirements

- Functional: compress image before `save_async`; no change to Gemini vision path
- Non-functional: no regression in meal analysis accuracy; compressed size ≤ 400KB; dimensions ≤ 768px longest axis

## Architecture

```
Before:
  file_contents (5MB) → save_async → Cloudinary (5MB)
  file_contents (5MB) → _compress_image → 200KB → Gemini

After:
  file_contents (5MB) → compress_image() → ~400KB → save_async → Cloudinary (~400KB)
  file_contents (5MB) → _compress_image (in VisionAIService, unchanged) → 200KB → Gemini
```

One compression pass per handler, separate from the vision service's own compression. The vision service's `_compress_image` is left in place (it will be a no-op on already-small images since the early-return condition handles them).

## Related Code Files

- **Create:** `src/infra/utils/image_compression.py`
- **Modify:** `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- **Modify:** `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py` (same pattern)
- **Create:** `tests/unit/infra/utils/test_image_compression.py`

## Implementation Steps

### Step 1 — Create shared compression utility

Create `src/infra/utils/image_compression.py`:

```python
"""Shared image compression utility — resize to max dimension, encode as JPEG."""
import logging
from io import BytesIO

from PIL import Image

logger = logging.getLogger(__name__)

_MAX_DIM = 768
_MAX_BYTES = 200 * 1024


def compress_image(image_bytes: bytes, max_dim: int = _MAX_DIM) -> bytes:
    """Resize to max_dim on longest axis, encode as JPEG quality=85.

    Returns original bytes unchanged if already a small JPEG within limits.
    Never raises — falls back to original on PIL errors.
    """
    try:
        img = Image.open(BytesIO(image_bytes))
        w, h = img.size
        if img.format == "JPEG" and max(w, h) <= max_dim and len(image_bytes) < _MAX_BYTES:
            return image_bytes
        if max(w, h) > max_dim:
            ratio = max_dim / max(w, h)
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

Verify `src/infra/utils/__init__.py` exists (create empty if missing):
```bash
ls src/infra/utils/
```

### Step 2 — Write unit tests

Create `tests/unit/infra/utils/test_image_compression.py`:

```python
from io import BytesIO
import pytest
from PIL import Image
from src.infra.utils.image_compression import compress_image

def _make_jpeg(w: int, h: int, size_pad: int = 0) -> bytes:
    img = Image.new("RGB", (w, h), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()

def test_large_image_is_resized():
    raw = _make_jpeg(3000, 4000)
    result = compress_image(raw)
    img = Image.open(BytesIO(result))
    assert max(img.size) <= 768

def test_small_jpeg_returned_unchanged():
    raw = _make_jpeg(400, 300)
    assert len(raw) < 200 * 1024
    result = compress_image(raw)
    assert result == raw  # early return path

def test_png_converted_to_jpeg():
    img = Image.new("RGB", (100, 100), color=(0, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    result = compress_image(buf.getvalue())
    out = Image.open(BytesIO(result))
    assert out.format == "JPEG"

def test_corrupt_bytes_returns_original():
    bad = b"not an image"
    result = compress_image(bad)
    assert result == bad
```

Run: `pytest tests/unit/infra/utils/test_image_compression.py -v`
Expected: 4 PASS.

### Step 3 — Apply compression in upload handler before `save_async`

In `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`:

Add import at top:
```python
from src.infra.utils.image_compression import compress_image
```

In `_handle_parallel_upload`, replace the `save_async` call block (around line 127–132):

```python
# Before
image_url = await self.image_store.save_async(
    command.file_contents,
    command.content_type,
    image_id,
)

# After
compressed = compress_image(command.file_contents)
image_url = await self.image_store.save_async(
    compressed,
    "image/jpeg",  # always JPEG after compression
    image_id,
)
```

Also update the `MealImage` construction (around line 204–210) to record compressed size:
```python
# Before
image=MealImage(
    image_id=image_id,
    format="jpeg" if "jpeg" in command.content_type else "png",
    size_bytes=command.file_size_bytes,
    url=image_url,
),

# After
image=MealImage(
    image_id=image_id,
    format="jpeg",  # always JPEG after compression
    size_bytes=len(compressed),  # actual stored size
    url=image_url,
),
```

Note: `compressed` is in scope from the `save_async` block — move the variable to class-level in the method if it's defined in a try block. Check the actual method scope.

### Step 4 — Apply same pattern in ingredient recognition handler

Check `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py` for how it receives image bytes, and apply the same compress-before-use pattern if it also calls `image_store.save_async`.

```bash
grep -n "save_async\|file_contents\|image_bytes" src/app/handlers/command_handlers/recognize_ingredient_command_handler.py
```

Apply compress_image the same way if found.

### Step 5 — Verify `src/infra/utils/__init__.py` exists

```bash
ls src/infra/utils/__init__.py 2>/dev/null || touch src/infra/utils/__init__.py
```

### Step 6 — Run full test suite

```bash
pytest tests/ -x -q 2>&1 | tail -20
```

Expected: all existing tests pass, no regressions.

### Step 7 — Commit

```bash
git add src/infra/utils/image_compression.py \
        src/infra/utils/__init__.py \
        src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py \
        src/app/handlers/command_handlers/recognize_ingredient_command_handler.py \
        tests/unit/infra/utils/test_image_compression.py
git commit -m "perf: compress images before Cloudinary upload to reduce outbound bandwidth"
```

## Success Criteria

- [ ] `compress_image()` utility created at `src/infra/utils/image_compression.py`
- [ ] 4 unit tests pass for compression utility
- [ ] `_handle_parallel_upload` compresses before `save_async`; content_type always "image/jpeg"
- [ ] `MealImage.size_bytes` reflects compressed size
- [ ] Full test suite passes with no regressions
- [ ] Ingredient recognition handler updated if it calls `save_async`

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| 768px looks bad on high-DPI meal detail views | Can increase `max_dim` to 1200 if user reports quality issues; behavior is configurable |
| PNG alpha-channel meals show artifacts | `img.mode != "RGB"` convert handles RGBA and palette modes |
| `compressed` var out of scope for MealImage | Hoist `compressed` above try block or inline `len()` at compress site |

## Security Considerations

Compression runs on server-received bytes before storage. PIL's `Image.open()` is safe for untrusted input — it does not execute code; parse errors are caught and fall back to original.
