import math
from typing import Dict

from src.domain.model.tdee import TdeeRequest, TdeeResponse, MacroTargets, ActivityLevel, Sex, Goal


class TdeeCalculationService:
    """Domain service for TDEE and macro calculations."""
    
    # Activity multipliers from specification - updated to match Flutter enum
    ACTIVITY_MULTIPLIERS = {
        ActivityLevel.SEDENTARY: 1.2,
        ActivityLevel.LIGHT: 1.375,
        ActivityLevel.MODERATE: 1.55,
        ActivityLevel.ACTIVE: 1.725,    # Changed from VERY to ACTIVE
        ActivityLevel.EXTRA: 1.9
    }
    
    def calculate_tdee(self, request: TdeeRequest) -> TdeeResponse:
        """Calculate BMR, TDEE and macros based on the request."""
        bmr = self._calculate_bmr(request)
        tdee = self._calculate_tdee_from_bmr(bmr, request.activity_level)
        macro_targets = self._calculate_all_macro_targets(tdee, request.weight_kg, request.goal)
        
        return TdeeResponse(
            bmr=round(bmr, 1),
            tdee=round(tdee, 1),
            goal=request.goal,
            macros=macro_targets,
        )
    
    def _calculate_bmr(self, request: TdeeRequest) -> float:
        """Calculate BMR using Mifflin-St Jeor or Katch-McArdle formula."""
        if request.body_fat_pct is not None:
            # Use Katch-McArdle formula when body fat % is available
            lean_mass_kg = request.weight_kg * (1 - request.body_fat_pct / 100)
            return 370 + 21.6 * lean_mass_kg
        else:
            # Use Mifflin-St Jeor formula
            if request.sex == Sex.MALE:
                return 10 * request.weight_kg + 6.25 * request.height_cm - 5 * request.age + 5
            else:
                return 10 * request.weight_kg + 6.25 * request.height_cm - 5 * request.age - 161
    
    def _calculate_tdee_from_bmr(self, bmr: float, activity_level: ActivityLevel) -> float:
        """Calculate TDEE from BMR using activity multiplier."""
        multiplier = self.ACTIVITY_MULTIPLIERS[activity_level]
        return bmr * multiplier
    
    def _calculate_all_macro_targets(self, tdee: float, weight_kg: float, goal: Goal) -> MacroTargets:
        """Calculate macro targets for all three goals."""
        calories = 0

        if goal == Goal.MAINTENANCE:
            calories = tdee
        elif goal == Goal.CUTTING:
            calories = tdee * 0.8
        elif goal == Goal.BULKING:
            calories = tdee * 1.15
        
        protein_g = weight_kg * 2.205 * 0.8

        fat_percentage = 0.20 if goal == Goal.CUTTING else 0.25
        fat_calories = calories * fat_percentage
        fat_g = fat_calories / 9

        protein_calories = protein_g * 4

        carb_calories = calories - protein_calories - fat_calories
        carb_g = carb_calories / 4

        macro_targets = MacroTargets(
            calories=round(calories, 1),
            protein=round(protein_g, 1),
            fat=round(fat_g, 1),
            carbs=round(carb_g, 1)
        )

        return macro_targets 