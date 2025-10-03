from src.domain.constants import TDEEConstants
from src.domain.model.tdee import TdeeRequest, TdeeResponse, MacroTargets, ActivityLevel, Sex, Goal
from src.domain.services.bmr_calculator import BMRCalculatorFactory


class TdeeCalculationService:
    """
    Domain service for TDEE and macro calculations.
    
    Automatically selects the appropriate BMR calculation formula:
    - Katch-McArdle: When body fat % is provided (more accurate)
    - Mifflin-St Jeor: When body fat % is not provided (standard approach)
    """
    
    def calculate_tdee(self, request: TdeeRequest) -> TdeeResponse:
        """Calculate BMR, TDEE and macros based on the request."""
        bmr, formula_name = self._calculate_bmr(request)
        tdee = self._calculate_tdee_from_bmr(bmr, request.activity_level)
        macro_targets = self._calculate_all_macro_targets(tdee, request.weight_kg, request.goal)
        return TdeeResponse(
            bmr=round(bmr, 1),
            tdee=round(tdee, 1),
            goal=request.goal,
            macros=macro_targets,
            formula_used=formula_name,
        )
    
    def _calculate_bmr(self, request: TdeeRequest) -> tuple[float, str]:
        """
        Calculate BMR using the appropriate formula based on available data.
        
        Returns:
            tuple: (bmr_value, formula_name)
        """
        # Get the appropriate calculator
        has_body_fat = request.body_fat_pct is not None
        calculator = BMRCalculatorFactory.get_calculator(has_body_fat)

        # Calculate BMR
        bmr = calculator.calculate(
            weight_kg=request.weight_kg,
            height_cm=request.height_cm,
            age=request.age,
            sex=request.sex,
            body_fat_pct=request.body_fat_pct
        )

        return bmr, calculator.get_formula_name()
    
    def _calculate_tdee_from_bmr(self, bmr: float, activity_level: ActivityLevel) -> float:
        """Calculate TDEE from BMR using activity multiplier."""
        # Map ActivityLevel enum to string for constants lookup
        activity_map = {
            ActivityLevel.SEDENTARY: "sedentary",
            ActivityLevel.LIGHT: "light",
            ActivityLevel.MODERATE: "moderate",
            ActivityLevel.ACTIVE: "active",
            ActivityLevel.EXTRA: "extra"
        }
        multiplier = TDEEConstants.ACTIVITY_MULTIPLIERS[activity_map[activity_level]]
        return bmr * multiplier
    
    def _calculate_all_macro_targets(self, tdee: float, weight_kg: float, goal: Goal) -> MacroTargets:
        """Calculate macro targets using Moderate Carb (30/35/35) split."""
        calories = 0

        if goal == Goal.MAINTENANCE:
            calories = tdee
        elif goal == Goal.CUTTING:
            calories = tdee - TDEEConstants.CUTTING_DEFICIT
        elif goal == Goal.BULKING:
            calories = tdee + TDEEConstants.BULKING_SURPLUS
        
        # Calculate macros using 30/35/35 split (Protein/Fat/Carbs)
        protein_calories = calories * TDEEConstants.PROTEIN_PERCENT
        fat_calories = calories * TDEEConstants.FAT_PERCENT
        carb_calories = calories * TDEEConstants.CARBS_PERCENT
        
        # Convert to grams (protein: 4 cal/g, fat: 9 cal/g, carbs: 4 cal/g)
        protein_g = protein_calories / 4
        fat_g = fat_calories / 9
        carb_g = carb_calories / 4

        macro_targets = MacroTargets(
            calories=round(calories, 1),
            protein=round(protein_g, 1),
            fat=round(fat_g, 1),
            carbs=round(carb_g, 1)
        )

        return macro_targets
    
    def calculate_macros(self, tdee: float, goal: Goal, weight_kg: float) -> MacroTargets:
        """Calculate macros based on TDEE, goal, and weight."""
        return self._calculate_all_macro_targets(tdee, weight_kg, goal) 