---
phase: 2
title: "Presigned Direct Upload"
status: pending
priority: P1
effort: "1d"
dependencies: []
---

# Phase 2: Presigned Direct Upload

## Overview

Eliminate the server → Cloudinary upload leg entirely. Server generates a signed Cloudinary upload token; client uploads the image directly to Cloudinary. Server receives the resulting URL and runs Gemini analysis.

Phase 1 skipped — compression utility is created here inline (used in safe-path analysis).

**Expected result:** Server never touches image bytes during upload. Service-initiated bandwidth drops from ~5.2MB to ~200KB/scan (Gemini safe path) or ~1KB (URL Gemini path).

## Context Links

- Design doc: `plans/reports/brainstorm-260612-1046-service-initiated-bandwidth-reduction-report.md`
- Cloudinary store: `src/infra/adapters/cloudinary_image_store.py`
- Image store port: `src/domain/ports/image_store_port.py`
- Meals route: `src/api/routes/v1/meals.py`
- Gemini provider: `src/infra/services/ai/providers/gemini_provider.py`
- Broken URL analysis: `src/infra/adapters/vision_ai_service.py:150–183`
- Existing analyze-by-url command: `src/app/commands/meal/analyze_meal_image_by_url_command.py`

## Validation Interview Answers (Applied Here)

| Decision | Choice |
|----------|--------|
| ScanByUrlCommand | Create new `ScanByUrlCommand` — existing `AnalyzeMealImageByUrlCommand` has incompatible fields (`public_id`, `content_type`, `file_size_bytes`) |
| `ImageStorePort` | Add `generate_upload_signature` abstract method to port interface |
| 768px threshold | Fine for meal tracker UI |
| Phase 1 | Skipped — compression utility created inline in this phase |

## Requirements

- **Functional:**
  - `GET /api/v1/meals/upload-token` returns signed Cloudinary params + server-generated `image_id`
  - `POST /api/v1/meals/scan-by-url` accepts `image_url` + `image_id` (validates server issued it), triggers analysis
  - Domain allowlist: only `res.cloudinary.com` URLs accepted on `scan-by-url`
  - Backward-compatible: existing `POST /api/v1/meals/` (file upload) unchanged
- **Non-functional:**
  - Signature expires in 300s
  - Gemini URL path tested; gate behind safe fallback if not confirmed

## Architecture

```
New flow:
  1. Client  → GET /api/v1/meals/upload-token
  2. Server  → {image_id, cloud_name, api_key, timestamp, signature, folder, public_id}
  3. Client  → POST https://api.cloudinary.com/v1_1/{cloud_name}/image/upload
               (multipart: file, api_key, timestamp, signature, folder, public_id)
  4. Client  → POST /api/v1/meals/scan-by-url  {image_url, image_id, user_description?}
  5. Server  → safe path: httpx.get(url) → compress_image → bytes → Gemini
          OR → URL path: pass URL directly to Gemini (test first)
  6. Server  → return meal analysis result

Old flow (unchanged):
  Client → POST /api/v1/meals/ (multipart file) → server → Cloudinary → Gemini → result
```

## Related Code Files

- **Create:** `src/infra/utils/__init__.py` (new directory)
- **Create:** `src/infra/utils/image_compression.py`
- **Modify:** `src/domain/ports/image_store_port.py` — add `generate_upload_signature` abstract method
- **Modify:** `src/infra/adapters/cloudinary_image_store.py` — implement `generate_upload_signature`
- **Create:** `src/app/commands/meal/scan_by_url_command.py`
- **Modify:** `src/app/commands/meal/__init__.py` — export new command
- **Create:** `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- **Create:** `src/api/routes/v1/meal_upload_token.py` — GET /upload-token
- **Create:** `src/api/routes/v1/meal_scan_by_url.py` — POST /scan-by-url
- **Modify:** `src/api/main.py` (or router registration) — include new routes
- **Modify:** `src/infra/adapters/vision_ai_service.py` — fix `analyze_by_url_with_strategy`
- **Create:** `tests/unit/infra/utils/test_image_compression.py`
- **Create:** `tests/unit/infra/adapters/test_cloudinary_upload_signature.py`
- **Create:** `tests/unit/api/test_meal_upload_token.py`
- **Create:** `tests/unit/api/test_meal_scan_by_url.py`

## Implementation Steps

### Step 1 — Create `src/infra/utils/` directory + compression utility

```bash
# Verify directory does not exist (needs mkdir, not just touch)
ls src/infra/utils/ 2>/dev/null || (mkdir -p src/infra/utils && touch src/infra/utils/__init__.py)
```

Create `src/infra/utils/image_compression.py`:

```python
"""Shared image compression — resize to max dimension, encode as JPEG."""
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

Write `tests/unit/infra/utils/test_image_compression.py`:

```python
from io import BytesIO
from PIL import Image
from src.infra.utils.image_compression import compress_image


def _make_jpeg(w: int, h: int) -> bytes:
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
    assert compress_image(raw) == raw


def test_png_converted_to_jpeg():
    img = Image.new("RGB", (100, 100))
    buf = BytesIO()
    img.save(buf, format="PNG")
    result = compress_image(buf.getvalue())
    assert Image.open(BytesIO(result)).format == "JPEG"


def test_corrupt_bytes_returns_original():
    bad = b"not an image"
    assert compress_image(bad) == bad
```

Run: `pytest tests/unit/infra/utils/test_image_compression.py -v`
Expected: 4 PASS.

### Step 2 — Add `generate_upload_signature` to `ImageStorePort`

In `src/domain/ports/image_store_port.py`, add the abstract method alongside the existing ones:

```python
from abc import abstractmethod

@abstractmethod
def generate_upload_signature(self, image_id: str, ttl: int = 300) -> dict:
    """Return signed params for direct client upload to Cloudinary.

    Returns dict with: image_id, cloud_name, api_key, timestamp, signature, folder, public_id
    """
    ...
```

Check that the existing abstract methods use `@abstractmethod` — match the same pattern.

### Step 3 — Implement `generate_upload_signature` in `CloudinaryImageStore`

In `src/infra/adapters/cloudinary_image_store.py`, add:

```python
import os
import time
import cloudinary.utils

def generate_upload_signature(self, image_id: str, ttl: int = 300) -> dict:
    timestamp = int(time.time())
    folder = "mealtrack"
    public_id = f"{folder}/{image_id}"

    params_to_sign = {
        "timestamp": timestamp,
        "folder": folder,
        "public_id": public_id,
    }
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "")
    signature = cloudinary.utils.api_sign_request(params_to_sign, api_secret)

    return {
        "image_id": image_id,
        "cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME", ""),
        "api_key": os.getenv("CLOUDINARY_API_KEY", ""),
        "timestamp": timestamp,
        "signature": signature,
        "folder": folder,
        "public_id": public_id,
    }
```

Write `tests/unit/infra/adapters/test_cloudinary_upload_signature.py`:

```python
import time
from unittest.mock import patch
from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore


@patch.dict("os.environ", {
    "CLOUDINARY_CLOUD_NAME": "testcloud",
    "CLOUDINARY_API_KEY": "testkey",
    "CLOUDINARY_API_SECRET": "testsecret",
})
@patch("cloudinary.config")
def test_signature_fields(mock_cfg):
    store = CloudinaryImageStore()
    result = store.generate_upload_signature("abc-123")
    assert result["image_id"] == "abc-123"
    assert result["folder"] == "mealtrack"
    assert result["public_id"] == "mealtrack/abc-123"
    assert result["cloud_name"] == "testcloud"
    assert result["api_key"] == "testkey"
    assert isinstance(result["timestamp"], int)
    assert isinstance(result["signature"], str) and len(result["signature"]) > 0


@patch.dict("os.environ", {
    "CLOUDINARY_CLOUD_NAME": "testcloud",
    "CLOUDINARY_API_KEY": "testkey",
    "CLOUDINARY_API_SECRET": "testsecret",
})
@patch("cloudinary.config")
def test_timestamp_is_recent(mock_cfg):
    store = CloudinaryImageStore()
    result = store.generate_upload_signature("abc-123", ttl=300)
    assert abs(result["timestamp"] - int(time.time())) < 5
```

Run: `pytest tests/unit/infra/adapters/test_cloudinary_upload_signature.py -v`

### Step 4 — Create `ScanByUrlCommand`

Create `src/app/commands/meal/scan_by_url_command.py`:

```python
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class ScanByUrlCommand:
    user_id: str
    image_url: str
    public_id: str      # must match server-issued token (e.g. "mealtrack/<uuid>")
    user_description: Optional[str] = None
    target_date: Optional[date] = None
    language: str = "en"
```

Export from `src/app/commands/meal/__init__.py` — add:
```python
from src.app.commands.meal.scan_by_url_command import ScanByUrlCommand
```
and add `"ScanByUrlCommand"` to `__all__` if it exists.

### Step 5 — Create `ScanByUrlCommandHandler`

Create `src/app/handlers/command_handlers/scan_by_url_command_handler.py`:

```python
"""Handle ScanByUrlCommand — analysis of a client-uploaded Cloudinary image."""
import httpx

from src.app.commands.meal.scan_by_url_command import ScanByUrlCommand
from src.domain.ports.vision_ai_port import VisionAIPort
from src.infra.utils.image_compression import compress_image


class ScanByUrlCommandHandler:
    def __init__(self, vision_service: VisionAIPort):
        self._vision = vision_service

    async def handle(self, command: ScanByUrlCommand) -> dict:
        # Safe path: download → compress → bytes to Gemini
        # Switch to URL path after confirming Gemini URL support (Step 6 test)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(command.image_url)
            resp.raise_for_status()
        image_bytes = compress_image(resp.content)
        return await self._vision.analyze_with_strategy(
            image_bytes,
            strategy=None,  # TODO: wire strategy from command once confirmed
            language=command.language,
            user_description=command.user_description,
        )
```

**Note:** The exact `analyze_with_strategy` signature — check `src/domain/ports/vision_ai_port.py` and match it exactly. Adjust parameter names to match the existing port signature.

### Step 6 — Test Gemini URL support (manual, one-time)

Before building the URL path, verify whether LangChain can fetch a Cloudinary URL without the server downloading it.

Create `scripts/test_gemini_url_vision.py`:

```python
"""One-time test: verify Gemini can fetch a Cloudinary URL directly."""
import asyncio
import os
import sys

# Fill these in before running:
TEST_URL = "https://res.cloudinary.com/<your-cloud>/image/upload/mealtrack/<known-image-id>"


async def test():
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )
    msg = HumanMessage(content=[
        {"type": "text", "text": "What food is in this image? Reply in one sentence."},
        {"type": "image_url", "image_url": {"url": TEST_URL}},
    ])
    try:
        response = await llm.ainvoke([msg])
        print("SUCCESS:", response.content)
    except Exception as e:
        print("FAILED:", e)


asyncio.run(test())
```

Run: `python scripts/test_gemini_url_vision.py`

**If SUCCESS → URL path works:** Update `scan_by_url_command_handler.py` to call
`self._vision.analyze_by_url_with_strategy(command.image_url, strategy)` after fixing the bug in Step 8.

**If FAILED → safe path only:** Keep the `httpx.get` + `compress_image` path. Step 7 (fix `analyze_by_url_with_strategy`) is still useful for future use but not required for launch.

### Step 7 — Create `GET /api/v1/meals/upload-token` endpoint

Check how existing routes are registered (look at `src/api/main.py` or route registration file).

Create `src/api/routes/v1/meal_upload_token.py`:

```python
"""GET /api/v1/meals/upload-token — returns signed Cloudinary upload params."""
import uuid
from fastapi import APIRouter, Depends

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.image_store import get_image_store
from src.domain.ports.image_store_port import ImageStorePort

router = APIRouter(prefix="/meals", tags=["meals"])


@router.get("/upload-token")
async def get_upload_token(
    user_id: str = Depends(get_current_user_id),
    image_store: ImageStorePort = Depends(get_image_store),
) -> dict:
    """Short-lived signed Cloudinary upload token for direct client upload."""
    image_id = str(uuid.uuid4())
    return image_store.generate_upload_signature(image_id)
```

**Note:** If the dependency injection pattern uses a different factory name than `get_image_store`, grep for it: `grep -rn "ImageStorePort" src/api/dependencies/ --include="*.py"` and use the correct name.

### Step 8 — Create `POST /api/v1/meals/scan-by-url` endpoint

Create `src/api/routes/v1/meal_scan_by_url.py`:

```python
"""POST /api/v1/meals/scan-by-url — analyze a meal from a Cloudinary URL."""
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from src.api.dependencies.auth import get_current_user_id

router = APIRouter(prefix="/meals", tags=["meals"])

_CLOUDINARY_DOMAIN_RE = re.compile(r"^https://res\.cloudinary\.com/")


class ScanByUrlRequest(BaseModel):
    image_url: str
    image_id: str           # must match the server-issued token's image_id
    user_description: str | None = None
    target_date: str | None = None
    language: str = "en"

    @field_validator("image_url")
    @classmethod
    def must_be_cloudinary(cls, v: str) -> str:
        if not _CLOUDINARY_DOMAIN_RE.match(v):
            raise ValueError("image_url must be a res.cloudinary.com URL")
        return v


@router.post("/scan-by-url")
async def scan_by_url(
    payload: ScanByUrlRequest,
    user_id: str = Depends(get_current_user_id),
    # Wire in command bus / handler via DI — check pattern used in existing endpoints
):
    from src.app.commands.meal.scan_by_url_command import ScanByUrlCommand
    # Verify image_id is in the expected folder structure to prevent path traversal
    expected_prefix = f"mealtrack/{payload.image_id}"
    if expected_prefix not in payload.image_url:
        raise HTTPException(status_code=400, detail="image_url does not match image_id")

    command = ScanByUrlCommand(
        user_id=user_id,
        image_url=payload.image_url,
        public_id=expected_prefix,
        user_description=payload.user_description,
        language=payload.language,
    )
    # TODO: dispatch via command bus — grep for how existing endpoints dispatch commands
    # e.g.: result = await command_bus.send(command)
    return result
```

**IMPORTANT:** The command dispatch pattern varies per project. Grep existing meal endpoints:
```bash
grep -n "command_bus\|event_bus\|handler\.handle\|dispatch" src/api/routes/v1/meals.py | head -20
```
Match the exact dispatch pattern used in `meals.py`.

### Step 9 — Register new routes

In the router registration file (find it first):
```bash
grep -rn "include_router\|meal" src/api/main.py | head -20
```

Add:
```python
from src.api.routes.v1.meal_upload_token import router as upload_token_router
from src.api.routes.v1.meal_scan_by_url import router as scan_by_url_router

app.include_router(upload_token_router, prefix="/api/v1")
app.include_router(scan_by_url_router, prefix="/api/v1")
```

### Step 10 — Fix `analyze_by_url_with_strategy` (optional, needed for URL path)

Only required if Step 6 confirms URL path works. Current bug in `src/infra/adapters/vision_ai_service.py:167–172`:

```python
# BUG: encodes URL text as fake image bytes
image_data=image_url.encode("utf-8"),
```

Safe path fix — replace the broken method body:

```python
async def analyze_by_url_with_strategy(self, image_url: str, strategy) -> dict:
    """Download from URL, compress, analyze. Safe fallback if Gemini URL mode fails."""
    import httpx
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(image_url)
        resp.raise_for_status()
    image_bytes = self._compress_image(resp.content)
    return await self.analyze_with_strategy(image_bytes, strategy)
```

If URL path confirmed working (Step 6 passed), also update `generate_with_vision` in `src/infra/services/ai/providers/gemini_provider.py` to detect URL vs bytes:

```python
async def generate_with_vision(self, model, prompt, image_data, system_message=None, **kwargs):
    # Detect if image_data is a URL (passed as UTF-8 bytes)
    try:
        candidate = image_data.decode("utf-8")
        is_url = candidate.startswith("https://") or candidate.startswith("http://")
    except (UnicodeDecodeError, AttributeError):
        is_url = False

    if is_url:
        image_part = {"type": "image_url", "image_url": {"url": candidate}}
    else:
        import base64
        b64 = base64.b64encode(image_data).decode("utf-8")
        image_part = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}

    # ... rest of existing method, replace image_part construction
```

### Step 11 — Run full test suite

```bash
pytest tests/ -x -q 2>&1 | tail -30
```

Expected: all pass. Fix any import errors from new route registrations.

### Step 12 — Commit

```bash
git add src/infra/utils/ \
        src/domain/ports/image_store_port.py \
        src/infra/adapters/cloudinary_image_store.py \
        src/app/commands/meal/scan_by_url_command.py \
        src/app/commands/meal/__init__.py \
        src/app/handlers/command_handlers/scan_by_url_command_handler.py \
        src/api/routes/v1/meal_upload_token.py \
        src/api/routes/v1/meal_scan_by_url.py \
        src/api/main.py \
        tests/unit/infra/utils/ \
        tests/unit/infra/adapters/test_cloudinary_upload_signature.py \
        tests/unit/api/
git commit -m "feat: presigned Cloudinary upload token and scan-by-url endpoint"
```

## Success Criteria

- [ ] `src/infra/utils/image_compression.py` created; 4 unit tests pass
- [ ] `ImageStorePort.generate_upload_signature` abstract method added
- [ ] `CloudinaryImageStore.generate_upload_signature` implemented + tested
- [ ] `ScanByUrlCommand` created with `(user_id, image_url, public_id, user_description, target_date, language)`
- [ ] `ScanByUrlCommandHandler` created (safe path: httpx + compress + Gemini bytes)
- [ ] `GET /api/v1/meals/upload-token` returns valid signature (image_id, timestamp, api_key, signature, folder, public_id)
- [ ] `POST /api/v1/meals/scan-by-url` rejects non-Cloudinary URLs (400)
- [ ] `POST /api/v1/meals/scan-by-url` rejects mismatched image_id in URL (400)
- [ ] Existing `POST /api/v1/meals/` unchanged and passing
- [ ] Gemini URL test documented (scripts/test_gemini_url_vision.py result noted)
- [ ] Full test suite passes

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| `generate_upload_signature` missing from port causes injection failure | Step 2 adds abstract method before Step 3 implements it |
| `get_image_store` dependency not found | Grep `src/api/dependencies/` before wiring |
| Command dispatch pattern varies from assumption in Step 8 | Grep `meals.py` for actual pattern before writing endpoint |
| Gemini URL via LangChain downloads on our server anyway | Safe path (httpx + compress) is the default; URL path is optional enhancement |
| Client's `image_id` in URL forged by attacker | `expected_prefix not in image_url` check in endpoint prevents arbitrary paths |
| Signature replay — attacker reuses valid token | Token is scoped to specific `public_id`; replay uploads same file, no privilege escalation |
| `src/infra/utils/` does not exist | Step 1 explicitly uses `mkdir -p` |

## Security Considerations

- Domain allowlist (`res.cloudinary.com` only) enforced server-side
- Server controls `image_id` (UUID); client cannot choose `public_id`
- Signature expires in 300s
- `CLOUDINARY_API_SECRET` never returned in token response
