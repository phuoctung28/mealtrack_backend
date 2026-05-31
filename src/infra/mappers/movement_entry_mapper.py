"""MovementEntry ORM <-> domain mapping functions."""

from src.domain.model.movement import MovementEntry
from src.infra.database.models.movement_entry import MovementEntryORM


def movement_entry_orm_to_domain(orm: MovementEntryORM) -> MovementEntry:
    return MovementEntry(
        id=orm.id,
        user_id=orm.user_id,
        activity_id=orm.activity_id,
        activity_name=orm.activity_name,
        duration_min=orm.duration_min,
        kcal_burned=orm.kcal_burned,
        intensity=orm.intensity,
        source=orm.source,
        include_in_balance=orm.include_in_balance,
        logged_at=orm.logged_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def movement_entry_domain_to_orm(domain: MovementEntry) -> MovementEntryORM:
    return MovementEntryORM(
        id=domain.id,
        user_id=domain.user_id,
        activity_id=domain.activity_id,
        activity_name=domain.activity_name,
        duration_min=domain.duration_min,
        kcal_burned=domain.kcal_burned,
        intensity=domain.intensity,
        source=domain.source,
        include_in_balance=domain.include_in_balance,
        logged_at=domain.logged_at,
    )
