"""
Service for generating meal suggestions.
"""
import logging
import uuid
from typing import List, Dict, Any, Optional

from src.domain.prompts.meal_suggestion_prompt import generate_meal_suggestion_prompt
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort

logger = logging.getLogger(__name__)


class MealSuggestionService:
    """
    Service for generating exactly 3 meal suggestions based on user inputs.
    
    Reuses the MealGenerationService for AI generation with specialized prompts.
    """
    
    def __init__(self, meal_generation_service: MealGenerationServicePort):
        """Initialize the service with meal generation adapter."""
        self.meal_generation_service = meal_generation_service
    
    def generate_suggestions(
        self,
        user_id: str,
        meal_type: str,
        calorie_target: int,
        ingredients: List[str],
        time_available_minutes: Optional[int],
        dietary_preferences: List[str],
    ) -> Dict[str, Any]:
        """
        Generate exactly 3 meal suggestions.
        
        Args:
            user_id: User identifier
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            calorie_target: Target calories for the meal
            ingredients: Available ingredients
            time_available_minutes: Optional time constraint in minutes
            dietary_preferences: Dietary preferences
            exclude_ids: Meal IDs to exclude (for regeneration)
        
        Returns:
            Dict with request_id, suggestions (list of 3), and generation_token
        """
        try:
            # Generate prompt
            prompt, system_message = generate_meal_suggestion_prompt(
                meal_type=meal_type,
                calorie_target=calorie_target,
                ingredients=ingredients,
                time_available_minutes=time_available_minutes,
                dietary_preferences=dietary_preferences,
                exclude_names=[]  # We'll use IDs for exclusion, names for prompt clarity
            )
            
            # Call AI generation service
            logger.info(f"Generating meal suggestions for user {user_id}, meal_type: {meal_type}")
            raw_response = self.meal_generation_service.generate_meal_plan(
                prompt=prompt,
                system_message=system_message,
                response_type="json",
                max_tokens=2000  # Sufficient for 3 meals
            )
            
            # Validate response structure
            if "suggestions" not in raw_response:
                raise ValueError("AI response missing 'suggestions' field")
            
            suggestions_list = raw_response["suggestions"]
            
            if not isinstance(suggestions_list, list):
                raise ValueError("'suggestions' field must be a list")
            
            if len(suggestions_list) < 3:
                logger.warning(f"AI generated only {len(suggestions_list)} suggestions, expected 3")
                # Pad with fallback if needed
                while len(suggestions_list) < 3:
                    suggestions_list.append(self._create_fallback_suggestion(meal_type, calorie_target))
            
            # Take only first 3 if more were generated
            suggestions_list = suggestions_list[:3]
            
            # Process and enrich suggestions
            processed_suggestions = []
            for idx, suggestion in enumerate(suggestions_list):
                processed = self._process_suggestion(suggestion, meal_type, idx)
                
                # Apply time filter if specified
                if time_available_minutes:
                    total_time = processed.get("estimated_cook_time_minutes", 0)
                    if total_time > time_available_minutes:
                        logger.warning(
                            f"Suggestion '{processed['name']}' exceeds time limit "
                            f"({total_time} > {time_available_minutes}), replacing with fallback"
                        )
                        processed = self._create_fallback_suggestion(
                            meal_type, calorie_target, time_available_minutes
                        )
                
                processed_suggestions.append(processed)
            
            # Generate unique IDs for tracking
            request_id = f"req_{uuid.uuid4().hex[:12]}"
            generation_token = f"gen_{uuid.uuid4().hex[:12]}"
            
            return {
                "request_id": request_id,
                "suggestions": processed_suggestions,
                "generation_token": generation_token
            }
            
        except Exception as e:
            logger.error(f"Error generating meal suggestions: {str(e)}")
            # Return fallback suggestions
            return self._generate_fallback_suggestions(user_id, meal_type, calorie_target, time_available_minutes)
    
    def _process_suggestion(self, suggestion: Dict[str, Any], meal_type: str, index: int) -> Dict[str, Any]:
        """
        Process and validate a single suggestion from AI response.
        
        Args:
            suggestion: Raw suggestion from AI
            meal_type: Type of meal
            index: Index in the list (for ID generation)
        
        Returns:
            Processed suggestion with all required fields
        """
        # Generate unique ID
        suggestion_id = f"meal_{meal_type}_{uuid.uuid4().hex[:8]}"
        
        # Extract and validate fields
        name = suggestion.get("name", f"Suggested {meal_type.title()} {index + 1}")
        description = suggestion.get("description", f"A delicious {meal_type}")
        
        prep_time = suggestion.get("prep_time", 10)
        cook_time = suggestion.get("cook_time", 15)
        total_time = prep_time + cook_time
        
        calories = int(suggestion.get("calories", 400))
        protein = float(suggestion.get("protein", 20.0))
        carbs = float(suggestion.get("carbs", 40.0))
        fat = float(suggestion.get("fat", 15.0))
        
        ingredients = suggestion.get("ingredients", [])
        seasonings = suggestion.get("seasonings", [])
        instructions = suggestion.get("instructions", [])
        
        # Combine ingredients and seasonings for ingredients_list
        ingredients_list = ingredients + seasonings
        
        # Build tags
        tags = []
        if suggestion.get("is_vegetarian", False):
            tags.append("vegetarian")
        if suggestion.get("is_vegan", False):
            tags.append("vegan")
        if suggestion.get("is_gluten_free", False):
            tags.append("gluten-free")
        
        cuisine_type = suggestion.get("cuisine_type", "International")
        if cuisine_type:
            tags.append(cuisine_type.lower())
        
        return {
            "id": suggestion_id,
            "name": name,
            "description": description,
            "estimated_cook_time_minutes": total_time,
            "calories": calories,
            "macros": {
                "protein": protein,
                "carbs": carbs,
                "fat": fat
            },
            "ingredients_list": ingredients_list,
            "instructions": instructions,
            "tags": tags,
            "image_url": None,
            "source": "AI Generated"
        }
    
    def _create_fallback_suggestion(
        self, 
        meal_type: str, 
        calorie_target: int,
        time_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a simple fallback suggestion when AI generation fails.
        
        Args:
            meal_type: Type of meal
            calorie_target: Target calories
            time_limit: Optional time constraint
        
        Returns:
            Fallback suggestion dict
        """
        suggestion_id = f"meal_{meal_type}_{uuid.uuid4().hex[:8]}"
        
        # Simple fallback meals by type
        fallback_meals = {
            "breakfast": {
                "name": "Simple Breakfast Bowl",
                "description": "Quick and nutritious breakfast with eggs and toast",
                "ingredients": ["2 eggs", "2 slices whole wheat bread", "1 tbsp butter"],
                "instructions": ["Toast bread", "Scramble eggs", "Serve together"]
            },
            "lunch": {
                "name": "Quick Lunch Plate",
                "description": "Balanced lunch with protein and vegetables",
                "ingredients": ["150g chicken breast", "100g mixed vegetables", "100g rice"],
                "instructions": ["Cook chicken", "Steam vegetables", "Prepare rice", "Serve together"]
            },
            "dinner": {
                "name": "Simple Dinner",
                "description": "Easy and satisfying dinner",
                "ingredients": ["200g protein of choice", "150g vegetables", "100g grains"],
                "instructions": ["Prepare protein", "Cook vegetables", "Prepare grains", "Combine and serve"]
            },
            "snack": {
                "name": "Healthy Snack",
                "description": "Quick and nutritious snack",
                "ingredients": ["1 apple", "2 tbsp peanut butter"],
                "instructions": ["Slice apple", "Serve with peanut butter"]
            }
        }
        
        fallback = fallback_meals.get(meal_type, fallback_meals["lunch"])
        
        # Adjust time if needed
        cook_time = 15 if time_limit and time_limit < 30 else 20
        
        return {
            "id": suggestion_id,
            "name": fallback["name"],
            "description": fallback["description"],
            "estimated_cook_time_minutes": cook_time,
            "calories": calorie_target,
            "macros": {
                "protein": calorie_target * 0.3 / 4,  # 30% protein
                "carbs": calorie_target * 0.4 / 4,    # 40% carbs
                "fat": calorie_target * 0.3 / 9       # 30% fat
            },
            "ingredients_list": fallback["ingredients"],
            "instructions": fallback["instructions"],
            "tags": ["simple", "quick"],
            "image_url": None,
            "source": "Fallback"
        }
    
    def _generate_fallback_suggestions(
        self,
        user_id: str,
        meal_type: str,
        calorie_target: int,
        time_limit: Optional[int]
    ) -> Dict[str, Any]:
        """
        Generate 3 fallback suggestions when AI generation completely fails.
        
        Returns:
            Complete response with 3 fallback suggestions
        """
        logger.warning(f"Using fallback suggestions for user {user_id}")
        
        suggestions = [
            self._create_fallback_suggestion(meal_type, calorie_target, time_limit)
            for _ in range(3)
        ]
        
        return {
            "request_id": f"req_fallback_{uuid.uuid4().hex[:12]}",
            "suggestions": suggestions,
            "generation_token": f"gen_fallback_{uuid.uuid4().hex[:12]}"
        }


