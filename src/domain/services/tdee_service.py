from src.domain.constants import TDEEConstants, NutritionConstants
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
        """Calculate macro targets using weight-based approach.

        Weight-based calculation (more accurate than percentage-based):
        - Protein: g/kg body weight (higher during cut to preserve muscle)
        - Fat: g/kg body weight (essential for hormone production)
        - Carbs: Remaining calories after protein and fat
        """
        # Determine target calories based on goal
        if goal == Goal.CUT:
            calories = tdee - TDEEConstants.CUTTING_DEFICIT
            goal_key = "cut"
        elif goal == Goal.BULK:
            calories = tdee + TDEEConstants.BULKING_SURPLUS
            goal_key = "bulk"
        elif goal == Goal.RECOMP:
            calories = tdee + TDEEConstants.RECOMP_ADJUSTMENT
            goal_key = "recomp"
        else:
            calories = tdee
            goal_key = "recomp"

        # Calculate protein from body weight (g/kg)
        protein_multiplier = TDEEConstants.PROTEIN_PER_KG.get(goal_key, 1.8)
        protein_g = weight_kg * protein_multiplier
        protein_g = max(TDEEConstants.MIN_PROTEIN_G, min(protein_g, TDEEConstants.MAX_PROTEIN_G))

        # Calculate fat from body weight (g/kg)
        fat_multiplier = TDEEConstants.FAT_PER_KG.get(goal_key, 0.9)
        fat_g = weight_kg * fat_multiplier
        fat_g = max(TDEEConstants.MIN_FAT_G, min(fat_g, TDEEConstants.MAX_FAT_G))

        # Calculate carbs from remaining calories
        protein_cals = protein_g * NutritionConstants.CALORIES_PER_GRAM_PROTEIN
        fat_cals = fat_g * NutritionConstants.CALORIES_PER_GRAM_FAT
        remaining_cals = calories - protein_cals - fat_cals
        carb_g = max(TDEEConstants.MIN_CARBS_G, remaining_cals / NutritionConstants.CALORIES_PER_GRAM_CARBS)

        return MacroTargets(
            calories=round(calories, 1),
            protein=round(protein_g, 1),
            fat=round(fat_g, 1),
            carbs=round(carb_g, 1)
        )
    
    def calculate_macros(self, tdee: float, goal: Goal, weight_kg: float) -> MacroTargets:
        """Calculate macros based on TDEE, goal, and weight.

        Args:
            tdee: Total Daily Energy Expenditure in calories
            goal: Fitness goal (CUT, BULK, RECOMP)
            weight_kg: Body weight in kilograms (must be within valid range)

        Returns:
            MacroTargets with calculated macros

        Raises:
            ValueError: If weight_kg is outside valid range
        """
        if not TDEEConstants.MIN_WEIGHT_KG <= weight_kg <= TDEEConstants.MAX_WEIGHT_KG:
            raise ValueError(
                f"weight_kg must be between {TDEEConstants.MIN_WEIGHT_KG} and "
                f"{TDEEConstants.MAX_WEIGHT_KG}, got {weight_kg}"
            )
        return self._calculate_all_macro_targets(tdee, weight_kg, goal) 