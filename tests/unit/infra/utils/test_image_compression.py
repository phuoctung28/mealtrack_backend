"""Unit tests for the image_compression utility."""

from io import BytesIO

import pytest
from PIL import Image

from src.infra.utils.image_compression import compress_image, _MAX_DIM, _MAX_BYTES


def _make_jpeg(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def _make_png(width: int, height: int) -> bytes:
    img = Image.new("RGBA", (width, height), color=(100, 150, 200, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _image_size(data: bytes) -> tuple[int, int]:
    return Image.open(BytesIO(data)).size


class TestCompressImage:
    def test_large_image_is_resized(self):
        raw = _make_jpeg(2000, 1500)
        result = compress_image(raw)
        w, h = _image_size(result)
        assert max(w, h) <= _MAX_DIM

    def test_small_jpeg_within_limits_returned_unchanged(self):
        raw = _make_jpeg(400, 300)
        # Ensure the raw bytes are genuinely small
        assert len(raw) < _MAX_BYTES
        result = compress_image(raw)
        assert result is raw  # same object — no recompression

    def test_png_converted_to_jpeg(self):
        raw = _make_png(200, 200)
        result = compress_image(raw)
        img = Image.open(BytesIO(result))
        assert img.format == "JPEG"

    def test_corrupt_bytes_falls_back_to_original(self):
        corrupt = b"not an image at all"
        result = compress_image(corrupt)
        assert result is corrupt  # unchanged fallback
