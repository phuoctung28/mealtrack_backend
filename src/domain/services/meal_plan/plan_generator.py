"""
Consolidated meal plan generator.
Merges meal_plan_generator.py, ingredient_based_meal_plan_service.py, 
and weekly_ingredient_based_meal_plan_service.py.
"""
import logging
from datetime import date, timedelta
from typing import List, Optional, Dict, Any

from src.domain.model.meal_planning import (
    MealPlan,
    DayPlan,
    PlannedMeal,
    MealGenerationRequest,
    MealGenerationType,
)
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.prompts import PromptTemplateManager
from src.domain.services.meal_plan.meal_plan_formatter import MealPlanFormatter

logger = logging.getLogger(__name__)


class PlanGenerator:
    """
    Generates meal plans using AI.
    
    Consolidates:
    - meal_plan_generator.py
    - ingredient_based_meal_plan_service.py
    - weekly_ingredient_based_meal_plan_service.py
    
    Supports:
    - Weekly ingredient-based plans
    - Daily ingredient-based plans
    - Profile-based plans
    """

    def __init__(
        self,
        generation_service: MealGenerationServicePort,
        formatter: Optional[MealPlanFormatter] = None,
    ):
        """
        Initialize generator.
        
        Args:
            generation_service: AI generation service port
            formatter: Optional plan formatter
        """
        self._generation = generation_service
        self._formatter = formatter or MealPlanFormatter()

    async def generate(self, request: MealGenerationRequest) -> MealPlan:
        """
        Generate a meal plan based on request type.
        
        Args:
            request: Generation request
            
        Returns:
            Generated MealPlan
        """
        if request.generation_type == MealGenerationType.WEEKLY_INGREDIENT_BASED:
            return await self._generate_weekly_ingredient_plan(request)
        elif request.generation_type == MealGenerationType.DAILY_INGREDIENT_BASED:
            return await self._generate_daily_ingredient_plan(request)
        elif request.generation_type == MealGenerationType.DAILY_PROFILE_BASED:
            return await self._generate_profile_plan(request)
        else:
            raise ValueError(f"Unsupported generation type: {request.generation_type}")

    async def generate_single_day(
        self,
        request: MealGenerationRequest,
        target_date: date,
    ) -> DayPlan:
        """
        Generate meals for a single day.
        
        Args:
            request: Generation request
            target_date: Target date
            
        Returns:
            DayPlan with generated meals
        """
        # Build prompt for single day
        prompt, system = self._build_daily_prompt(request)
        
        # Generate
        raw_result = await self._generation.generate_meal_plan(
            prompt=prompt,
            system_message=system,
            response_format="json",
            max_tokens=2000,
        )
        
        # Parse and format
        meals = self._formatter.parse_daily_response(raw_result)
        
        return DayPlan(
            date=target_date,
            day_name=target_date.strftime("%A"),
            meals=meals,
        )

    async def _generate_weekly_ingredient_plan(
        self,
        request: MealGenerationRequest,
    ) -> MealPlan:
        """Generate weekly plan from ingredients."""
        logger.info(f"Generating weekly ingredient plan for {request.user_id}")
        
        prompt, system = self._build_weekly_ingredient_prompt(request)
        
        raw_result = await self._generation.generate_meal_plan(
            prompt=prompt,
            system_message=system,
            response_format="json",
            max_tokens=8000,
        )
        
        days = self._formatter.parse_weekly_response(raw_result, request.start_date)
        
        return MealPlan(
            id=f"plan_{request.user_id}_{request.start_date.isoformat()}",
            user_id=request.user_id,
            start_date=request.start_date,
            end_date=request.start_date + timedelta(days=6),
            days=days,
            nutrition_targets=request.nutrition_targets,
        )

    async def _generate_daily_ingredient_plan(
        self,
        request: MealGenerationRequest,
    ) -> MealPlan:
        """Generate daily plan from ingredients."""
        logger.info(f"Generating daily ingredient plan for {request.user_id}")
        
        prompt, system = self._build_daily_prompt(request)
        
        raw_result = await self._generation.generate_meal_plan(
            prompt=prompt,
            system_message=system,
            response_format="json",
            max_tokens=2000,
        )
        
        meals = self._formatter.parse_daily_response(raw_result)
        
        return MealPlan(
            id=f"plan_{request.user_id}_{request.start_date.isoformat()}",
            user_id=request.user_id,
            start_date=request.start_date,
            end_date=request.start_date,
            days=[MealPlanDay(
                date=request.start_date,
                day_name=request.start_date.strftime("%A"),
                meals=meals,
            )],
            nutrition_targets=request.nutrition_targets,
        )

    async def _generate_profile_plan(
        self,
        request: MealGenerationRequest,
    ) -> MealPlan:
        """Generate plan based on user profile only."""
        logger.info(f"Generating profile-based plan for {request.user_id}")
        
        prompt, system = self._build_profile_prompt(request)
        
        raw_result = await self._generation.generate_meal_plan(
            prompt=prompt,
            system_message=system,
            response_format="json",
            max_tokens=2000,
        )
        
        meals = self._formatter.parse_daily_response(raw_result)
        
        return MealPlan(
            id=f"plan_{request.user_id}_{request.start_date.isoformat()}",
            user_id=request.user_id,
            start_date=request.start_date,
            end_date=request.start_date,
            days=[MealPlanDay(
                date=request.start_date,
                day_name=request.start_date.strftime("%A"),
                meals=meals,
            )],
            nutrition_targets=request.nutrition_targets,
        )

    def _build_weekly_ingredient_prompt(
        self,
        request: MealGenerationRequest,
    ) -> tuple[str, str]:
        """Build prompt for weekly ingredient-based plan."""
        targets = request.nutrition_targets
        ingredients = request.ingredients or []
        seasonings = request.seasonings or []
        
        # Use PromptTemplateManager for compressed prompts
        ingredients_str = ", ".join(ingredients[:15]) if ingredients else "common ingredients"
        seasonings_str = ", ".join(seasonings[:10]) if seasonings else "salt, pepper, herbs"
        
        prompt = f"""Generate 7-day meal plan using ONLY these ingredients.

INGREDIENTS: {ingredients_str}
SEASONINGS: {seasonings_str}

DAILY TARGETS: {targets.calories}cal, {targets.protein}g P, {targets.carbs}g C, {targets.fat}g F

{PromptTemplateManager.get_ingredient_rules()}
{PromptTemplateManager.get_seasoning_rules()}

Return JSON:
{PromptTemplateManager.get_json_schema("weekly_meal")}
"""
        
        return prompt, PromptTemplateManager.get_system_message("meal_planning")

    def _build_daily_prompt(
        self,
        request: MealGenerationRequest,
    ) -> tuple[str, str]:
        """Build prompt for daily plan."""
        targets = request.nutrition_targets
        ingredients = request.ingredients or []
        
        ingredients_str = ", ".join(ingredients[:10]) if ingredients else "common ingredients"
        
        prompt = f"""Generate daily meal plan.

INGREDIENTS: {ingredients_str}
TARGETS: {targets.calories}cal, {targets.protein}g P, {targets.carbs}g C, {targets.fat}g F

{PromptTemplateManager.get_ingredient_rules()}

Return JSON:
{PromptTemplateManager.get_json_schema("daily_meal")}
"""
        
        return prompt, PromptTemplateManager.get_system_message("meal_planning")

    def _build_profile_prompt(
        self,
        request: MealGenerationRequest,
    ) -> tuple[str, str]:
        """Build prompt for profile-based plan."""
        profile = request.user_profile
        targets = request.nutrition_targets
        
        goal_guidance = PromptTemplateManager.get_goal_guidance(profile.fitness_goal)
        
        prompt = f"""Generate daily meal plan for user profile.

PROFILE: {profile.fitness_goal} ({goal_guidance}), {profile.activity_level} activity
DIET: {', '.join(profile.dietary_preferences or ['none'])}
TARGETS: {targets.calories}cal, {targets.protein}g P, {targets.carbs}g C, {targets.fat}g F

Return JSON:
{PromptTemplateManager.get_json_schema("daily_meal")}
"""
        
        return prompt, PromptTemplateManager.get_system_message("nutritionist")
