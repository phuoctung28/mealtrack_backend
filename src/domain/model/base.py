"""Base class for all domain models."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


def validate_uuid(value: str, field_name: str) -> None:
    """Validate UUID format, raise ValueError if invalid."""
    if not isinstance(value, str):
        raise ValueError(
            f"Expected string for {field_name}, got {type(value).__name__}"
        )
    try:
        uuid.UUID(value)
    except ValueError as e:
        raise ValueError(f"Invalid UUID format for {field_name}: {value}") from e


@dataclass(kw_only=True)
class BaseDomainModel:
    """Base for all domain models.

    Provides:
        id: UUIDv4 identifier (auto-generated if not provided)
        created_at: Timestamp when entity was created (populated from DB)
        updated_at: Timestamp when entity was last modified (populated from DB)
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime | None = None
    updated_at: datetime | None = None
