"""WeeklyMacroBudget ORM <-> domain mapping functions."""
from src.domain.model.weekly import WeeklyMacroBudget
from src.infra.database.models.weekly.weekly_macro_budget import WeeklyMacroBudgetORM


def weekly_budget_orm_to_domain(orm: WeeklyMacroBudgetORM) -> WeeklyMacroBudget:
    return WeeklyMacroBudget(
        weekly_budget_id=orm.weekly_budget_id,
        user_id=orm.user_id,
        week_start_date=orm.week_start_date,
        target_calories=orm.target_calories,
        target_protein=orm.target_protein,
        target_carbs=orm.target_carbs,
        target_fat=orm.target_fat,
        consumed_calories=orm.consumed_calories,
        consumed_protein=orm.consumed_protein,
        consumed_carbs=orm.consumed_carbs,
        consumed_fat=orm.consumed_fat,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def weekly_budget_domain_to_orm(domain: WeeklyMacroBudget) -> WeeklyMacroBudgetORM:
    return WeeklyMacroBudgetORM(
        weekly_budget_id=domain.weekly_budget_id,
        user_id=domain.user_id,
        week_start_date=domain.week_start_date,
        target_calories=domain.target_calories,
        target_protein=domain.target_protein,
        target_carbs=domain.target_carbs,
        target_fat=domain.target_fat,
        consumed_calories=domain.consumed_calories,
        consumed_protein=domain.consumed_protein,
        consumed_carbs=domain.consumed_carbs,
        consumed_fat=domain.consumed_fat,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )
