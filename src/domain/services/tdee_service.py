from src.domain.constants import TDEEConstants
from src.domain.model.user import TdeeRequest, TdeeResponse, MacroTargets, ActivityLevel, Goal
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
        """Calculate macro targets using goal-specific ratios based on nutrition science.

        Different goals require different macro distributions:
        - Bulking: Higher carbs for training energy, moderate protein
        - Cutting: Higher protein to preserve muscle, lower carbs
        - Maintenance: Balanced approach like bulking
        - Recomp: High protein like cutting, moderate carbs for training
        """
        # Determine target calories based on goal
        if goal == Goal.MAINTENANCE:
            calories = tdee
            goal_key = "maintenance"
        elif goal == Goal.CUTTING:
            calories = tdee - TDEEConstants.CUTTING_DEFICIT
            goal_key = "cutting"
        elif goal == Goal.BULKING:
            calories = tdee + TDEEConstants.BULKING_SURPLUS
            goal_key = "bulking"
        elif goal == Goal.RECOMP:
            calories = tdee + TDEEConstants.RECOMP_ADJUSTMENT
            goal_key = "recomp"
        else:
            # Fallback to maintenance for unknown goals
            calories = tdee
            goal_key = "maintenance"

        # Get goal-specific macro ratios
        macro_ratios = TDEEConstants.MACRO_RATIOS.get(goal_key, TDEEConstants.MACRO_RATIOS["maintenance"])

        # Calculate macros using goal-specific ratios
        # Protein: 4 cal/g, Carbs: 4 cal/g, Fat: 9 cal/g
        protein_g = (calories * macro_ratios["protein"]) / 4
        carb_g = (calories * macro_ratios["carbs"]) / 4
        fat_g = (calories * macro_ratios["fat"]) / 9

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