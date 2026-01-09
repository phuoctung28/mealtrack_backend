"""
Meal plan orchestration service.
Consolidates meal_plan_orchestration_service.py and meal_plan_persistence_service.py.
"""
import logging
from datetime import date
from typing import Optional, List, Dict, Any

from src.domain.model.meal_planning import (
    MealPlan,
    MealGenerationRequest,
)
from src.domain.ports.meal_plan_repository_port import MealPlanRepositoryPort
from src.domain.services.meal_plan.meal_plan_validator import MealPlanValidator
from src.domain.services.meal_plan.plan_generator import PlanGenerator

logger = logging.getLogger(__name__)


class PlanOrchestrator:
    """
    Orchestrates meal plan generation and persistence.
    
    Consolidates:
    - meal_plan_orchestration_service.py
    - meal_plan_persistence_service.py
    
    Responsibilities:
    - Coordinate plan generation workflow
    - Handle persistence (save, update, delete)
    - Manage plan lifecycle
    """

    def __init__(
        self,
        generator: PlanGenerator,
        repository: MealPlanRepositoryPort,
        validator: Optional[MealPlanValidator] = None,
    ):
        """
        Initialize orchestrator.
        
        Args:
            generator: Plan generation service
            repository: Plan repository port
            validator: Optional plan validator
        """
        self._generator = generator
        self._repository = repository
        self._validator = validator or MealPlanValidator()

    async def generate_and_save_plan(
        self,
        request: MealGenerationRequest,
    ) -> MealPlan:
        """
        Generate a meal plan and persist it.
        
        Args:
            request: Generation request with user preferences
            
        Returns:
            Generated and saved MealPlan
            
        Raises:
            ValueError: If validation fails
        """
        logger.info(f"Generating plan for user {request.user_id}")
        
        # Generate plan
        plan = await self._generator.generate(request)
        
        # Validate
        errors = self._validator.validate(plan)
        if errors:
            logger.warning(f"Plan validation failed: {errors}")
            raise ValueError(f"Plan validation failed: {', '.join(errors)}")
        
        # Save
        saved_plan = await self._repository.save(plan)
        
        logger.info(f"Plan saved: {saved_plan.id}")
        return saved_plan

    async def get_user_plan(
        self,
        user_id: str,
        start_date: Optional[date] = None,
    ) -> Optional[MealPlan]:
        """
        Get user's current meal plan.
        
        Args:
            user_id: User ID
            start_date: Optional start date filter
            
        Returns:
            MealPlan or None if not found
        """
        return await self._repository.get_by_user(user_id, start_date)

    async def get_meals_by_date(
        self,
        user_id: str,
        target_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Get meals for a specific date.
        
        Args:
            user_id: User ID
            target_date: Date to get meals for
            
        Returns:
            List of meal dictionaries
        """
        plan = await self._repository.get_by_user(user_id)
        if not plan:
            return []
        
        # Find day in plan
        for day in plan.days:
            if day.date == target_date:
                return [meal.to_dict() for meal in day.meals]
        
        return []

    async def update_plan(
        self,
        plan_id: str,
        updates: Dict[str, Any],
    ) -> MealPlan:
        """
        Update an existing plan.
        
        Args:
            plan_id: Plan ID
            updates: Dictionary of updates
            
        Returns:
            Updated MealPlan
        """
        plan = await self._repository.get_by_id(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
        
        # Validate and save
        errors = self._validator.validate(plan)
        if errors:
            raise ValueError(f"Update validation failed: {', '.join(errors)}")
        
        return await self._repository.update(plan)

    async def delete_plan(self, plan_id: str) -> bool:
        """
        Delete a meal plan.
        
        Args:
            plan_id: Plan ID
            
        Returns:
            True if deleted, False otherwise
        """
        return await self._repository.delete(plan_id)

    async def regenerate_day(
        self,
        plan_id: str,
        target_date: date,
        request: MealGenerationRequest,
    ) -> MealPlan:
        """
        Regenerate meals for a specific day.
        
        Args:
            plan_id: Existing plan ID
            target_date: Day to regenerate
            request: Generation request
            
        Returns:
            Updated MealPlan
        """
        plan = await self._repository.get_by_id(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Generate new day
        new_day = await self._generator.generate_single_day(request, target_date)
        
        # Replace day in plan
        plan.days = [
            new_day if day.date == target_date else day
            for day in plan.days
        ]
        
        return await self._repository.update(plan)
