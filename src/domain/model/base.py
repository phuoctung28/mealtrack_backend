"""Base class for all domain models."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(kw_only=True)
class BaseDomainModel:
    """Base for all domain models.

    Provides:
        id: UUIDv4 identifier (auto-generated if not provided)
        created_at: Timestamp when entity was created (populated from DB)
        updated_at: Timestamp when entity was last modified (populated from DB)
    """
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None