import io

import pytest
from starlette.datastructures import UploadFile

from src.api.exceptions import ValidationException
from src.api.utils.file_validation import FileValidator


def _upload_file(content: bytes, content_type: str) -> UploadFile:
    return UploadFile(filename="x", file=io.BytesIO(content), headers={"content-type": content_type})


def test_validate_image_file_rejects_content_type():
    f = _upload_file(b"abc", "image/gif")
    with pytest.raises(ValidationException) as exc:
        FileValidator.validate_image_file(
            f, allowed_content_types=["image/jpeg", "image/png"], max_size_bytes=10
        )
    assert exc.value.error_code == "INVALID_FILE_TYPE"


def test_validate_image_file_rejects_too_large():
    f = _upload_file(b"a" * 11, "image/jpeg")
    with pytest.raises(ValidationException) as exc:
        FileValidator.validate_image_file(
            f, allowed_content_types=["image/jpeg"], max_size_bytes=10
        )
    assert exc.value.error_code == "FILE_TOO_LARGE"
    assert exc.value.details["size_bytes"] == 11


def test_validate_image_file_returns_bytes_and_resets_pointer():
    f = _upload_file(b"hello", "image/png")
    out = FileValidator.validate_image_file(
        f, allowed_content_types=["image/png"], max_size_bytes=10
    )
    assert out == b"hello"
    # Ensure pointer reset (so caller can re-read)
    assert f.file.tell() == 0


def test_validate_image_file_wraps_read_error():
    class _BadFile(io.BytesIO):
        def read(self, *args, **kwargs):  # type: ignore[override]
            raise RuntimeError("boom")

    f = UploadFile(filename="x", file=_BadFile(b"abc"), headers={"content-type": "image/jpeg"})
    with pytest.raises(ValidationException) as exc:
        FileValidator.validate_image_file(
            f, allowed_content_types=["image/jpeg"], max_size_bytes=10
        )
    assert exc.value.error_code == "FILE_READ_ERROR"

