from src.domain.constants import NutritionConstants, TDEEConstants
from src.domain.model.user import (
    Goal,
    JobType,
    MacroTargets,
    Sex,
    TdeeRequest,
    TdeeResponse,
    TrainingLevel,
)
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
        tdee = self._calculate_tdee_from_activity(bmr, request.job_type)
        macro_targets = self._calculate_all_macro_targets(
            tdee,
            request.weight_kg,
            request.goal,
            request.training_level,
            bmr=bmr,
            sex=request.sex,
        )
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
            body_fat_pct=request.body_fat_pct,
        )

        return bmr, calculator.get_formula_name()

    def _calculate_tdee_from_activity(self, bmr: float, job_type: JobType) -> float:
        """Calculate baseline TDEE from BMR using non-exercise activity.

        Logged movement entries credit workout calories separately. Planned
        training volume stays on the request for compatibility and protein
        context, but it must not inflate baseline calories.
        """
        base = TDEEConstants.JOB_TYPE_MULTIPLIERS.get(job_type.value, 1.2)
        return bmr * base

    def _calculate_all_macro_targets(
        self,
        tdee: float,
        weight_kg: float,
        goal: Goal,
        training_level: TrainingLevel = None,
        bmr: float = None,
        sex: Sex = None,
    ) -> MacroTargets:
        """Calculate macro targets using weight-based approach.

        Weight-based calculation (more accurate than percentage-based):
        - Protein: g/kg body weight (higher during cut to preserve muscle)
        - Fat: g/kg body weight (essential for hormone production)
        - Carbs: Remaining calories after protein and fat

        Args:
            tdee: Total Daily Energy Expenditure in calories
            weight_kg: Body weight in kilograms
            goal: Fitness goal (CUT, BULK, RECOMP)
            training_level: Optional training experience level for protein adjustment
            bmr: Basal Metabolic Rate for floor protection
            sex: Sex for clinical minimum floor (1200F/1500M)
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

        # Apply calorie floor: never below BMR or clinical minimum (1200F/1500M)
        # Industry standard used by MyFitnessPal, Noom, Lose It
        if bmr is not None and sex is not None:
            clinical_min = (
                TDEEConstants.MIN_CALORIES_FEMALE
                if sex == Sex.FEMALE
                else TDEEConstants.MIN_CALORIES_MALE
            )
            calories = max(calories, bmr, clinical_min)

        # Calculate protein from body weight (g/kg)
        # Use training-level-aware protein if provided, otherwise use default
        if training_level:
            training_key = training_level.value
            protein_multiplier = TDEEConstants.PROTEIN_PER_KG_BY_TRAINING.get(
                goal_key, {}
            ).get(training_key, TDEEConstants.PROTEIN_PER_KG.get(goal_key, 1.8))
        else:
            protein_multiplier = TDEEConstants.PROTEIN_PER_KG.get(goal_key, 1.8)
        protein_g = weight_kg * protein_multiplier
        protein_g = max(
            TDEEConstants.MIN_PROTEIN_G, min(protein_g, TDEEConstants.MAX_PROTEIN_G)
        )

        # Fat dual-gate: max(weight-based, percentage-based) for hormone safety
        # Dorgan 1996: <20% cal reduces testosterone; Kerksick 2018 ISSN
        fat_from_weight = weight_kg * TDEEConstants.FAT_PER_KG.get(goal_key, 0.9)
        fat_min_pct = TDEEConstants.FAT_MIN_PERCENT.get(goal_key, 0.25)
        fat_from_percent = (
            calories * fat_min_pct
        ) / NutritionConstants.CALORIES_PER_GRAM_FAT
        fat_g = max(fat_from_weight, fat_from_percent)
        fat_g = max(TDEEConstants.MIN_FAT_G, min(fat_g, TDEEConstants.MAX_FAT_G))

        # Calculate carbs from remaining calories
        # Note: carbs below 2.5 g/kg may impair resistance training performance
        # (Burke 2011, Escobar 2016). Expected in aggressive deficits.
        protein_cals = protein_g * NutritionConstants.CALORIES_PER_GRAM_PROTEIN
        fat_cals = fat_g * NutritionConstants.CALORIES_PER_GRAM_FAT
        remaining_cals = calories - protein_cals - fat_cals
        carb_g = max(
            TDEEConstants.MIN_CARBS_G,
            remaining_cals / NutritionConstants.CALORIES_PER_GRAM_CARBS,
        )

        # Round macros first, then derive calories from rounded macros
        rounded_protein = round(protein_g, 1)
        rounded_fat = round(fat_g, 1)
        rounded_carbs = round(carb_g, 1)
        derived_calories = (
            rounded_protein * NutritionConstants.CALORIES_PER_GRAM_PROTEIN
            + rounded_carbs * NutritionConstants.CALORIES_PER_GRAM_CARBS
            + rounded_fat * NutritionConstants.CALORIES_PER_GRAM_FAT
        )

        return MacroTargets(
            calories=round(derived_calories, 1),
            protein=rounded_protein,
            fat=rounded_fat,
            carbs=rounded_carbs,
        )

    def calculate_macros(
        self,
        tdee: float,
        goal: Goal,
        weight_kg: float,
        training_level: TrainingLevel = None,
    ) -> MacroTargets:
        """Calculate macros based on TDEE, goal, and weight.

        Note: BMR floor protection (1200F/1500M) is NOT applied by this method.
        Use calculate_tdee() for full floor protection.

        Args:
            tdee: Total Daily Energy Expenditure in calories
            goal: Fitness goal (CUT, BULK, RECOMP)
            weight_kg: Body weight in kilograms (must be within valid range)
            training_level: Optional training experience level for protein adjustment

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
        return self._calculate_all_macro_targets(tdee, weight_kg, goal, training_level)
