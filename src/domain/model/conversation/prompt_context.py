"""
Domain models for prompt generation context.
"""
from dataclasses import dataclass

from ..meal_planning.meal_generation_request import MealGenerationContext


@dataclass
class PromptContext:
    """Context for generating prompts."""
    generation_context: MealGenerationContext
    
    def get_ingredients_text(self) -> str:
        """Get formatted ingredients text."""
        if not self.generation_context.request.ingredient_constraints:
            return "common ingredients"
        
        ingredients = self.generation_context.request.ingredient_constraints.available_ingredients
        return ", ".join(ingredients) if ingredients else "common ingredients"
    
    def get_seasonings_text(self) -> str:
        """Get formatted seasonings text."""
        if not self.generation_context.request.ingredient_constraints:
            return "basic spices"
        
        seasonings = self.generation_context.request.ingredient_constraints.available_seasonings
        return ", ".join(seasonings) if seasonings else "basic spices"
    
    def get_dietary_requirements_text(self) -> str:
        """Get formatted dietary requirements."""
        prefs = self.generation_context.request.user_profile.dietary_preferences
        if not prefs:
            return ""
        return f"\nDietary preferences: {', '.join(prefs)}"
    
    def get_allergy_restrictions_text(self) -> str:
        """Get formatted allergy restrictions."""
        allergies = self.generation_context.request.user_profile.allergies
        if not allergies:
            return ""
        return f"\nAllergies to avoid: {', '.join(allergies)}"
    
    def get_calorie_guidance_text(self) -> str:
        """Get calorie guidance text."""
        calories = self.generation_context.request.nutrition_targets.calories
        if self.generation_context.is_weekly_plan():
            return f"\nDaily target: ~{calories} calories total per day"
        return f"\nTarget calories: {calories}"
    
    def get_meal_types_text(self) -> str:
        """Get formatted meal types text."""
        meal_types = [mt.value for mt in self.generation_context.meal_types]
        return ", ".join(meal_types)
    
    def get_goal_guidance(self) -> str:
        """Get goal-specific guidance text."""
        goal = self.generation_context.request.user_profile.fitness_goal
        
        goal_guidance_map = {
            'lose_weight': "Focus on high-volume, low-calorie foods with plenty of fiber and protein for satiety",
            'gain_weight': "Include calorie-dense, nutritious foods with healthy fats and complex carbs",
            'build_muscle': "Emphasize high protein content with complete amino acids",
            'maintain_weight': "Create balanced meals with appropriate portions"
        }
        
        return goal_guidance_map.get(goal, 'balanced nutrition')
    
    def get_week_dates_text(self) -> str:
        """Get formatted week dates for the prompt."""
        if not self.generation_context.start_date or not self.generation_context.end_date:
            return "Monday through Sunday"
        
        from datetime import timedelta
        dates = []
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for i, day_name in enumerate(day_names):
            day_date = self.generation_context.start_date + timedelta(days=i)
            dates.append(f"{day_name} ({day_date.strftime('%B %d, %Y')})")
        
        return ", ".join(dates)


@dataclass
class PromptTemplate:
    """Template for generating prompts."""
    template_text: str
    system_message: str
    
    def render(self, context: PromptContext) -> str:
        """Render the template with context."""
        # This would be implemented with proper template rendering
        # For now, return the template text (to be implemented properly)
        return self.template_text