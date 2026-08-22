import io

import pytest
from starlette.datastructures import UploadFile

from src.api.exceptions import ValidationException
from src.api.utils.file_validator import FileValidator


def _upload_file(content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        filename="x", file=io.BytesIO(content), headers={"content-type": content_type}
    )


@pytest.mark.asyncio
async def test_validate_image_file_rejects_content_type():
    f = _upload_file(b"abc", "image/gif")
    with pytest.raises(ValidationException):
        await FileValidator.validate_image_file(
            f, allowed_content_types=["image/jpeg", "image/png"], max_size_bytes=10
        )


@pytest.mark.asyncio
async def test_validate_image_file_rejects_too_large():
    f = _upload_file(b"a" * 11, "image/jpeg")
    with pytest.raises(ValidationException):
        await FileValidator.validate_image_file(
            f, allowed_content_types=["image/jpeg"], max_size_bytes=10
        )


@pytest.mark.asyncio
async def test_validate_image_file_rejects_empty():
    f = _upload_file(b"", "image/png")
    with pytest.raises(ValidationException):
        await FileValidator.validate_image_file(
            f, allowed_content_types=["image/png"], max_size_bytes=10
        )


@pytest.mark.asyncio
async def test_validate_image_file_returns_bytes_and_resets_position():
    f = _upload_file(b"hello", "image/png")
    out = await FileValidator.validate_image_file(
        f, allowed_content_types=["image/png"], max_size_bytes=10
    )
    assert out == b"hello"
    # Starlette's UploadFile exposes the underlying file object
    assert f.file.tell() == 0
