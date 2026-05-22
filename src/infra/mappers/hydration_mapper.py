"""HydrationEntry ORM <-> domain mapping functions."""

from src.domain.model.hydration.hydration_entry import HydrationEntry
from src.domain.model.hydration.hydration_enums import HydrationSource
from src.infra.database.models.hydration.hydration_log import HydrationLogORM


def hydration_entry_orm_to_domain(orm: HydrationLogORM) -> HydrationEntry:
    return HydrationEntry(
        entry_id=orm.id,
        user_id=orm.user_id,
        drink_id=orm.drink_id,
        volume_ml=orm.volume_ml,
        credited_ml=orm.credited_ml,
        source=HydrationSource(orm.source),
        meal_id=orm.meal_id,
        logged_at=orm.logged_at,
        created_at=orm.created_at,
        is_deleted=orm.is_deleted,
    )


def hydration_entry_domain_to_orm(entry: HydrationEntry) -> HydrationLogORM:
    return HydrationLogORM(
        id=entry.entry_id,
        user_id=entry.user_id,
        drink_id=entry.drink_id,
        volume_ml=entry.volume_ml,
        credited_ml=entry.credited_ml,
        source=entry.source.value if isinstance(entry.source, HydrationSource) else entry.source,
        meal_id=entry.meal_id,
        logged_at=entry.logged_at,
        is_deleted=entry.is_deleted,
    )
