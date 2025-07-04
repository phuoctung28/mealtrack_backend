"""Service for handling user onboarding and data persistence."""
from typing import Dict, Optional

from sqlalchemy.orm import Session

from src.domain.model.macro_targets import SimpleMacroTargets
from src.domain.model.tdee import TdeeRequest, Sex, ActivityLevel, Goal, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService
from src.infra.repositories.user_repository import UserRepository


class UserOnboardingService:
    """Service for processing user onboarding data."""
    
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.tdee_service = TdeeCalculationService()
    
    def save_onboarding_data(self, user_id: str, onboarding_data: Dict) -> Dict:
        """
        Save user onboarding data to the database.
        
        Args:
            user_id: The user's ID
            onboarding_data: Dictionary containing all onboarding sections:
                - personal_info: age, gender, height, weight, body_fat_percentage
                - activity_level: activity_level
                - fitness_goals: fitness_goal, target_weight
                - dietary_preferences: preferences list
                - health_conditions: conditions list
                - allergies: allergies list
                - meal_preferences: meals_per_day, snacks_per_day
        
        Returns:
            Dictionary with saved data and calculated TDEE/macros
        """
        try:
            # Extract data from sections
            personal_info = onboarding_data.get('personal_info', {})
            activity_data = onboarding_data.get('activity_level', {})
            fitness_data = onboarding_data.get('fitness_goals', {})
            dietary_data = onboarding_data.get('dietary_preferences', {})
            health_data = onboarding_data.get('health_conditions', {})
            allergy_data = onboarding_data.get('allergies', {})
            meal_prefs = onboarding_data.get('meal_preferences', {})
            
            # 1. Create/Update User Profile
            profile = self.user_repo.create_user_profile(
                user_id=user_id,
                age=personal_info.get('age'),
                gender=personal_info.get('gender'),
                height_cm=personal_info.get('height'),
                weight_kg=personal_info.get('weight'),
                body_fat_percentage=personal_info.get('body_fat_percentage')
            )
            
            # 2. Create/Update User Preferences
            preferences = self.user_repo.create_user_preferences(
                user_id=user_id,
                dietary_preferences=dietary_data.get('preferences', []),
                health_conditions=health_data.get('conditions', []),
                allergies=allergy_data.get('allergies', [])
            )
            
            # 3. Create/Update User Goal
            goal = self.user_repo.create_user_goal(
                user_id=user_id,
                activity_level=activity_data.get('activity_level'),
                fitness_goal=fitness_data.get('fitness_goal'),
                target_weight_kg=fitness_data.get('target_weight'),
                meals_per_day=meal_prefs.get('meals_per_day', 3),
                snacks_per_day=meal_prefs.get('snacks_per_day', 1)
            )
            
            # 4. Calculate TDEE and Macros
            tdee_result = self._calculate_tdee_and_macros(profile, goal)
            
            # 5. Save TDEE Calculation
            tdee_calc = self.user_repo.save_tdee_calculation(
                user_id=user_id,
                user_profile_id=profile.id,
                user_goal_id=goal.id,
                bmr=tdee_result['bmr'],
                tdee=tdee_result['tdee'],
                target_calories=tdee_result['target_calories'],
                macros=tdee_result['macros']
            )
            
            return {
                'success': True,
                'user_id': user_id,
                'profile_id': profile.id,
                'goal_id': goal.id,
                'tdee_calculation': {
                    'id': tdee_calc.id,
                    'bmr': tdee_calc.bmr,
                    'tdee': tdee_calc.tdee,
                    'target_calories': tdee_calc.target_calories,
                    'macros': {
                        'protein': tdee_calc.protein_grams,
                        'carbs': tdee_calc.carbs_grams,
                        'fat': tdee_calc.fat_grams
                    }
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_tdee_and_macros(self, profile: 'UserProfile', goal: 'UserGoal') -> Dict:
        """Calculate TDEE and macros based on profile and goal."""
        # Map database values to domain enums
        sex = Sex.MALE if profile.gender.lower() == 'male' else Sex.FEMALE
        
        activity_map = {
            'sedentary': ActivityLevel.SEDENTARY,
            'light': ActivityLevel.LIGHT,
            'moderate': ActivityLevel.MODERATE,
            'active': ActivityLevel.ACTIVE,
            'extra': ActivityLevel.EXTRA
        }
        
        goal_map = {
            'maintenance': Goal.MAINTENANCE,
            'cutting': Goal.CUTTING,
            'bulking': Goal.BULKING
        }
        
        # Create TDEE request
        tdee_request = TdeeRequest(
            age=profile.age,
            sex=sex,
            height=profile.height_cm,
            weight=profile.weight_kg,
            body_fat_pct=profile.body_fat_percentage,
            activity_level=activity_map.get(goal.activity_level, ActivityLevel.MODERATE),
            goal=goal_map.get(goal.fitness_goal, Goal.MAINTENANCE),
            unit_system=UnitSystem.METRIC
        )
        
        # Calculate TDEE
        tdee_result = self.tdee_service.calculate_tdee(tdee_request)
        
        # Create SimpleMacroTargets
        macros = SimpleMacroTargets(
            protein=tdee_result.macros.protein,
            carbs=tdee_result.macros.carbs,
            fat=tdee_result.macros.fat
        )
        
        return {
            'bmr': tdee_result.bmr,
            'tdee': tdee_result.tdee,
            'target_calories': tdee_result.tdee,  # Can be adjusted based on goal
            'macros': macros
        }
    
    def get_user_onboarding_summary(self, user_id: str) -> Optional[Dict]:
        """Get a summary of user's onboarding data."""
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return None
        
        profile = self.user_repo.get_current_user_profile(user_id)
        preferences = self.user_repo.get_user_preferences(user_id)
        goal = self.user_repo.get_current_user_goal(user_id)
        latest_tdee = self.user_repo.get_latest_tdee_calculation(user_id)
        
        if not all([profile, goal]):
            return None
        
        summary = {
            'user_id': user_id,
            'personal_info': {
                'age': profile.age,
                'gender': profile.gender,
                'height': profile.height_cm,
                'weight': profile.weight_kg,
                'body_fat_percentage': profile.body_fat_percentage
            },
            'fitness_info': {
                'activity_level': goal.activity_level,
                'fitness_goal': goal.fitness_goal,
                'target_weight': goal.target_weight_kg,
                'meals_per_day': goal.meals_per_day,
                'snacks_per_day': goal.snacks_per_day
            }
        }
        
        if preferences:
            summary['preferences'] = {
                'dietary': [dp.preference for dp in preferences.dietary_preferences],
                'health_conditions': [hc.condition for hc in preferences.health_conditions],
                'allergies': [a.allergen for a in preferences.allergies]
            }
        
        if latest_tdee:
            summary['latest_calculation'] = {
                'date': latest_tdee.calculation_date.isoformat(),
                'bmr': latest_tdee.bmr,
                'tdee': latest_tdee.tdee,
                'target_calories': latest_tdee.target_calories,
                'macros': {
                    'protein': latest_tdee.protein_grams,
                    'carbs': latest_tdee.carbs_grams,
                    'fat': latest_tdee.fat_grams
                }
            }
        
        return summary