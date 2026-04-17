"""
Weekly macro budget repository.
"""
import uuid
from datetime import date
from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.domain.model.weekly import WeeklyMacroBudget
from src.infra.database.models.weekly import WeeklyMacroBudget as DBWeeklyMacroBudget


class WeeklyBudgetRepository:
    """Repository for weekly macro budget operations."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_user_and_week(self, user_id: str, week_start_date: date) -> Optional[WeeklyMacroBudget]:
        """Find a weekly budget by user and week start date."""
        db_budget = self.db.query(DBWeeklyMacroBudget).filter(
            DBWeeklyMacroBudget.user_id == user_id,
            DBWeeklyMacroBudget.week_start_date == week_start_date
        ).first()

        if db_budget:
            return db_budget.to_domain()
        return None

    def _upsert_stmt(self, budget: WeeklyMacroBudget):
        """Build a PostgreSQL INSERT ... ON CONFLICT DO UPDATE statement."""
        values = {
            "weekly_budget_id": budget.weekly_budget_id,
            "user_id": budget.user_id,
            "week_start_date": budget.week_start_date,
            "target_calories": budget.target_calories,
            "target_protein": budget.target_protein,
            "target_carbs": budget.target_carbs,
            "target_fat": budget.target_fat,
            "consumed_calories": budget.consumed_calories,
            "consumed_protein": budget.consumed_protein,
            "consumed_carbs": budget.consumed_carbs,
            "consumed_fat": budget.consumed_fat,
        }

        stmt = pg_insert(DBWeeklyMacroBudget).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_user_week",
            set_={
                "target_calories": stmt.excluded.target_calories,
                "target_protein": stmt.excluded.target_protein,
                "target_carbs": stmt.excluded.target_carbs,
                "target_fat": stmt.excluded.target_fat,
            },
        )
        return stmt

    def upsert(self, budget: WeeklyMacroBudget) -> WeeklyMacroBudget:
        """Insert a weekly budget or update targets on conflict (uq_user_week)."""
        if not budget.weekly_budget_id:
            budget.weekly_budget_id = str(uuid.uuid4())
        stmt = self._upsert_stmt(budget)
        self.db.execute(stmt)
        self.db.commit()

        # Re-fetch to return the persisted state (may have been updated by conflict)
        self.db.expire_all()
        db_budget = self.db.query(DBWeeklyMacroBudget).filter(
            DBWeeklyMacroBudget.user_id == budget.user_id,
            DBWeeklyMacroBudget.week_start_date == budget.week_start_date,
        ).first()
        if db_budget is None:
            raise RuntimeError(
                f"upsert succeeded but re-fetch returned None "
                f"(user_id={budget.user_id}, week_start_date={budget.week_start_date})"
            )
        return db_budget.to_domain()

    def create(self, budget: WeeklyMacroBudget) -> WeeklyMacroBudget:
        """Create a new weekly budget (delegates to upsert for race-safety)."""
        return self.upsert(budget)

    def update(self, budget: WeeklyMacroBudget) -> WeeklyMacroBudget:
        """Update an existing weekly budget."""
        db_budget = self.db.query(DBWeeklyMacroBudget).filter(
            DBWeeklyMacroBudget.weekly_budget_id == budget.weekly_budget_id
        ).first()

        if db_budget:
            db_budget.target_calories = budget.target_calories
            db_budget.target_protein = budget.target_protein
            db_budget.target_carbs = budget.target_carbs
            db_budget.target_fat = budget.target_fat
            db_budget.consumed_calories = budget.consumed_calories
            db_budget.consumed_protein = budget.consumed_protein
            db_budget.consumed_carbs = budget.consumed_carbs
            db_budget.consumed_fat = budget.consumed_fat

            self.db.commit()
            self.db.refresh(db_budget)
            return db_budget.to_domain()

        return budget

    def delete(self, weekly_budget_id: str) -> bool:
        """Delete a weekly budget."""
        db_budget = self.db.query(DBWeeklyMacroBudget).filter(
            DBWeeklyMacroBudget.weekly_budget_id == weekly_budget_id
        ).first()

        if db_budget:
            self.db.delete(db_budget)
            self.db.commit()
            return True
        return False
