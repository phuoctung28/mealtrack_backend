"""Tests for domain model base utilities."""

import pytest

from src.domain.model.base import validate_uuid


@pytest.mark.unit
class TestValidateUuid:
    def test_valid_uuid4(self):
        validate_uuid("550e8400-e29b-41d4-a716-446655440000", "test_field")

    def test_valid_uuid_uppercase(self):
        validate_uuid("550E8400-E29B-41D4-A716-446655440000", "test_field")

    def test_invalid_uuid_raises(self):
        with pytest.raises(ValueError) as exc_info:
            validate_uuid("not-a-uuid", "user_id")
        assert "Invalid UUID format for user_id" in str(exc_info.value)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError) as exc_info:
            validate_uuid("", "order_id")
        assert "Invalid UUID format for order_id" in str(exc_info.value)

    def test_none_raises(self):
        with pytest.raises(ValueError) as exc_info:
            validate_uuid(None, "user_id")  # type: ignore[arg-type]
        assert "Expected string for user_id" in str(exc_info.value)
        assert "NoneType" in str(exc_info.value)
