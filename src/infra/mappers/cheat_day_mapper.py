"""CheatDay ORM <-> domain mapping functions."""
from src.domain.model.cheat_day import CheatDay
from src.infra.database.models.cheat_day.cheat_day import CheatDayORM


def cheat_day_orm_to_domain(orm: CheatDayORM) -> CheatDay:
    return CheatDay(
        cheat_day_id=orm.id,
        user_id=orm.user_id,
        date=orm.date,
        marked_at=orm.marked_at,
    )


def cheat_day_domain_to_orm(domain: CheatDay) -> CheatDayORM:
    return CheatDayORM(
        id=domain.cheat_day_id,
        user_id=domain.user_id,
        date=domain.date,
        marked_at=domain.marked_at,
    )
