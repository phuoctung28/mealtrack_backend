"""
Weekly macro budget repository.
"""
import uuid
from datetime import date
from typing import Optional

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

    def create(self, budget: WeeklyMacroBudget) -> WeeklyMacroBudget:
        """Create a new weekly budget."""
        if not budget.weekly_budget_id:
            budget.weekly_budget_id = str(uuid.uuid4())

        db_budget = DBWeeklyMacroBudget.from_domain(budget)
        self.db.add(db_budget)
        self.db.commit()
        self.db.refresh(db_budget)

        return db_budget.to_domain()

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
