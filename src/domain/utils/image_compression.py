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
