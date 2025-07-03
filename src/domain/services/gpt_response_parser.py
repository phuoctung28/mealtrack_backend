import json
from typing import Dict, Any, List, Optional

from src.domain.model.macros import Macros
from src.domain.model.nutrition import Nutrition, FoodItem


class GPTResponseParsingError(Exception):
    """Exception raised for errors in parsing GPT responses."""
    pass

class GPTResponseParser:
    """
    Service for parsing GPT Vision API responses into domain models.
    
    This class implements US-2.2 - Parse the GPT response to structured food list and macros.
    """
    
    def parse_to_nutrition(self, gpt_response: Dict[str, Any]) -> Nutrition:
        """
        Parse GPT response into Nutrition domain model.
        
        Args:
            gpt_response: Response from the OpenAI Vision API
            
        Returns:
            Nutrition object with food items and macros
            
        Raises:
            GPTResponseParsingError: If parsing fails due to invalid format
        """
        try:
            # Get the structured data part
            data = gpt_response.get("structured_data")
            if not data:
                raise GPTResponseParsingError("No structured data found in GPT response")
            
            # Parse food items
            food_items = self._parse_food_items(data)
            
            # Get total macros
            total_macros = self._calculate_total_macros(data, food_items)
            
            # Get total calories
            total_calories = self._calculate_total_calories(data, food_items, total_macros)
            
            # Get confidence score
            confidence_score = float(data.get("confidence", 0.5))
            confidence_score = min(max(0.0, confidence_score), 1.0)
            
            # Create Nutrition object
            nutrition = Nutrition(
                calories=total_calories,
                macros=total_macros,
                micros=None,  # No micros from GPT
                food_items=food_items if food_items else None,
                confidence_score=confidence_score
            )
            
            return nutrition
            
        except (KeyError, ValueError, TypeError) as e:
            raise GPTResponseParsingError(f"Failed to parse GPT response: {str(e)}")
    
    def _parse_food_items(self, data: Dict[str, Any]) -> List[FoodItem]:
        """Parse food items from GPT response data."""
        food_items = []
        if "foods" in data:
            for food_data in data["foods"]:
                # Validate required fields
                required_fields = ["name", "quantity", "unit", "calories", "macros"]
                for field in required_fields:
                    if field not in food_data:
                        raise GPTResponseParsingError(f"Missing required field '{field}' in food item")
                
                # Create Macros object
                macros_data = food_data["macros"]
                macros = Macros(
                    protein=float(macros_data.get("protein", 0)),
                    carbs=float(macros_data.get("carbs", 0)),
                    fat=float(macros_data.get("fat", 0)),
                    fiber=float(macros_data.get("fiber", 0)) if "fiber" in macros_data else None
                )
                
                # Create FoodItem with confidence score
                confidence = 1.0  # Default confidence
                if "confidence" in food_data:
                    confidence = min(max(0.0, float(food_data["confidence"])), 1.0)
                
                food_item = FoodItem(
                    name=food_data["name"],
                    quantity=float(food_data["quantity"]),
                    unit=food_data["unit"],
                    calories=float(food_data["calories"]),
                    macros=macros,
                    micros=None,  # GPT doesn't provide micros yet
                    confidence=confidence
                )
                
                food_items.append(food_item)
        
        return food_items
    
    def _calculate_total_macros(self, data: Dict[str, Any], food_items: List[FoodItem]) -> Macros:
        """Calculate total macros based on food items and top-level macros if available."""
        if food_items:
            total_protein = sum(item.macros.protein for item in food_items)
            total_carbs = sum(item.macros.carbs for item in food_items)
            total_fat = sum(item.macros.fat for item in food_items)
            
            # Calculate fiber, handling None values
            fibers = [item.macros.fiber for item in food_items if item.macros.fiber is not None]
            total_fiber = sum(fibers) if fibers else None
            
            total_macros = Macros(
                protein=total_protein,
                carbs=total_carbs,
                fat=total_fat,
                fiber=total_fiber
            )
        else:
            # If no food items, use top-level macros if available
            if "macros" in data:
                total_macros = Macros(
                    protein=float(data["macros"].get("protein", 0)),
                    carbs=float(data["macros"].get("carbs", 0)),
                    fat=float(data["macros"].get("fat", 0)),
                    fiber=float(data["macros"].get("fiber", 0)) if "fiber" in data["macros"] else None
                )
            else:
                # Default empty macros
                total_macros = Macros(protein=0.0, carbs=0.0, fat=0.0)
        
        return total_macros
    
    def _calculate_total_calories(self, data: Dict[str, Any], food_items: List[FoodItem], total_macros: Macros) -> float:
        """Calculate total calories based on food items and top-level calories if available."""
        if "total_calories" in data:
            return float(data["total_calories"])
        else:
            # Calculate from food items if available
            total_calories = sum(item.calories for item in food_items) if food_items else total_macros.total_calories
            return total_calories
    
    def parse_dish_name(self, gpt_response: Dict[str, Any]) -> Optional[str]:
        """
        Parse dish name from GPT response.
        
        Args:
            gpt_response: Response from the OpenAI Vision API
            
        Returns:
            Dish name string or None if not found
        """
        try:
            structured_data = gpt_response.get("structured_data", {})
            return structured_data.get("dish_name")
        except (KeyError, TypeError):
            return None
    
    def extract_raw_json(self, gpt_response: Dict[str, Any]) -> str:
        """
        Extract the raw JSON from GPT response as a string.
        
        Args:
            gpt_response: Response from the OpenAI Vision API
            
        Returns:
            JSON string representation
        """
        try:
            # If raw_response exists, we prefer that for storage
            if "raw_response" in gpt_response:
                return gpt_response["raw_response"]
            
            # Otherwise, just stringify the structured data
            return json.dumps(gpt_response["structured_data"])
        except (KeyError, TypeError):
            return json.dumps(gpt_response) 