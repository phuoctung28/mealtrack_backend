from io import BytesIO
from unittest.mock import MagicMock, patch

from PIL import Image

from src.infra.adapters.vision_ai_service import VisionAIService

_MGR_PATCH = "src.infra.adapters.vision_ai_service.GeminiModelManager"


def test_vision_service_disables_thinking_and_caps_output():
    with patch(_MGR_PATCH) as mock_cls:
        mock_mgr = MagicMock()
        mock_cls.get_instance.return_value = mock_mgr

        VisionAIService()

        mock_cls.get_instance.assert_called_once()
        mock_mgr.get_model.assert_called_once_with(
            thinking_budget=0, max_output_tokens=1024
        )


def _make_jpeg(width: int, height: int, quality: int = 95) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _make_service() -> VisionAIService:
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
    small_bytes = _make_jpeg(400, 300, quality=50)
    assert len(small_bytes) < 200 * 1024  # confirm precondition

    result = service._compress_image(small_bytes)

    assert result is small_bytes  # skip path returns original object unchanged


def test_compress_image_fallback_on_corrupt_bytes():
    service = _make_service()
    corrupt = b"not an image at all"

    result = service._compress_image(corrupt)

    assert result == corrupt
