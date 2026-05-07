"""WeightEntry ORM <-> domain mapping functions."""

from src.domain.model.weight import WeightEntry
from src.infra.database.models.weight_entry import WeightEntryORM


def weight_entry_orm_to_domain(orm: WeightEntryORM) -> WeightEntry:
    return WeightEntry(
        id=orm.id,
        user_id=orm.user_id,
        weight_kg=orm.weight_kg,
        recorded_at=orm.recorded_at,
        created_at=orm.created_at,
    )


def weight_entry_domain_to_orm(domain: WeightEntry) -> WeightEntryORM:
    return WeightEntryORM(
        id=domain.id,
        user_id=domain.user_id,
        weight_kg=domain.weight_kg,
        recorded_at=domain.recorded_at,
    )
