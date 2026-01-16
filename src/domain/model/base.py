"""Base class for all domain models."""
from dataclasses import dataclass, field
import uuid


@dataclass(kw_only=True)
class BaseDomainModel:
    """Base for all domain models, providing a UUIDv4 id."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)