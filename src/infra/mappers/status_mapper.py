"""
Status mapper utility to convert between domain and database enums.
Centralizes status mapping logic to avoid duplication.
"""
from src.domain.model.meal import MealStatus
from src.infra.database.models.enums import MealStatusEnum


class MealStatusMapper:
    """Maps meal status between domain and database layers."""

    DOMAIN_TO_DB = {
        MealStatus.PROCESSING: MealStatusEnum.PROCESSING,
        MealStatus.ANALYZING: MealStatusEnum.ANALYZING,
        MealStatus.ENRICHING: MealStatusEnum.ENRICHING,
        MealStatus.READY: MealStatusEnum.READY,
        MealStatus.FAILED: MealStatusEnum.FAILED,
        MealStatus.INACTIVE: MealStatusEnum.INACTIVE,
    }

    DB_TO_DOMAIN = {
        MealStatusEnum.PROCESSING: MealStatus.PROCESSING,
        MealStatusEnum.ANALYZING: MealStatus.ANALYZING,
        MealStatusEnum.ENRICHING: MealStatus.ENRICHING,
        MealStatusEnum.READY: MealStatus.READY,
        MealStatusEnum.FAILED: MealStatus.FAILED,
        MealStatusEnum.INACTIVE: MealStatus.INACTIVE,
    }

    @classmethod
    def to_db(cls, domain_status: MealStatus) -> MealStatusEnum:
        """Convert domain status to database enum."""
        return cls.DOMAIN_TO_DB[domain_status]

    @classmethod
    def to_domain(cls, db_status: MealStatusEnum) -> MealStatus:
        """Convert database enum to domain status."""
        return cls.DB_TO_DOMAIN[db_status]
