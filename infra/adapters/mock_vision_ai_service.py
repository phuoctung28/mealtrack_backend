import json
import logging
import uuid
from typing import Dict, Any

from domain.ports.vision_ai_service_port import VisionAIServicePort

logger = logging.getLogger(__name__)

class MockVisionAIService(VisionAIServicePort):
    """Mock implementation for testing without external dependencies."""
    
    def __init__(self):
        logger.info("Using MockVisionAIService - no external AI dependencies required")
    
    def analyze(self, image_bytes: bytes, strategy=None) -> Dict[str, Any]:
        """Analyze image using the provided strategy."""
        if strategy is None:
            return self._generate_mock_response("basic")
        
        strategy_name = strategy.get_strategy_name().lower()
        
        if "portion" in strategy_name:
            return self._handle_portion_strategy(strategy)
        elif "ingredient" in strategy_name:
            return self._handle_ingredient_strategy(strategy)
        else:
            return self._generate_mock_response("basic")
    
    def _handle_portion_strategy(self, strategy) -> Dict[str, Any]:
        """Handle portion-aware strategy."""
        response = self._generate_mock_response("portion")
        
        if hasattr(strategy, 'portion_size') and hasattr(strategy, 'unit'):
            portion_size = strategy.portion_size
            unit = strategy.unit
            ratio = portion_size / 150.0  # 150g baseline
            
            structured_data = response["structured_data"]
            for food in structured_data["foods"]:
                food["quantity"] = round(food["quantity"] * ratio, 1)
                food["calories"] = round(food["calories"] * ratio)
                for macro in food["macros"]:
                    food["macros"][macro] = round(food["macros"][macro] * ratio, 1)
            
            structured_data["total_calories"] = round(structured_data["total_calories"] * ratio)
            structured_data["portion_adjustment"] = f"Adjusted for {portion_size} {unit}"
        
        return response
    
    def _handle_ingredient_strategy(self, strategy) -> Dict[str, Any]:
        """Handle ingredient-aware strategy."""
        response = self._generate_mock_response("ingredients")
        
        if hasattr(strategy, 'ingredients'):
            ingredients = strategy.ingredients
            
            total_calories = sum(ing.get("calories", 0) for ing in ingredients)
            total_protein = sum(ing.get("macros", {}).get("protein", 0) for ing in ingredients)
            total_carbs = sum(ing.get("macros", {}).get("carbs", 0) for ing in ingredients)
            total_fat = sum(ing.get("macros", {}).get("fat", 0) for ing in ingredients)
            total_fiber = sum(ing.get("macros", {}).get("fiber", 0) for ing in ingredients)
            
            structured_data = response["structured_data"]
            structured_data.update({
                "total_calories": total_calories,
                "confidence": 0.95,
                "ingredient_based": True,
                "combined_nutrition": "Calculated based on provided ingredients",
                "foods": [{
                    "name": "Combined Meal",
                    "quantity": 1.0,
                    "unit": "serving",
                    "calories": total_calories,
                    "macros": {
                        "protein": total_protein,
                        "carbs": total_carbs,
                        "fat": total_fat,
                        "fiber": total_fiber
                    }
                }]
            })
        
        return response
    
    def _generate_mock_response(self, context_type: str = "basic") -> Dict[str, Any]:
        """Generate a realistic mock response."""
        foods = [
            {
                "name": "Grilled Chicken Breast",
                "quantity": 120.0,
                "unit": "g",
                "calories": 200,
                "macros": {"protein": 37.2, "carbs": 0.0, "fat": 4.3, "fiber": 0.0}
            },
            {
                "name": "Brown Rice",
                "quantity": 150.0,
                "unit": "g",
                "calories": 195,
                "macros": {"protein": 4.5, "carbs": 40.0, "fat": 1.5, "fiber": 3.5}
            },
            {
                "name": "Steamed Broccoli",
                "quantity": 100.0,
                "unit": "g",
                "calories": 35,
                "macros": {"protein": 3.7, "carbs": 6.8, "fat": 0.4, "fiber": 2.6}
            }
        ]
        
        confidence_map = {"basic": 0.8, "portion": 0.85, "ingredients": 0.95}
        
        mock_json_response = {
            "foods": foods,
            "total_calories": sum(food["calories"] for food in foods),
            "confidence": confidence_map.get(context_type, 0.8),
            "analysis_id": str(uuid.uuid4()),
            "mock_response": True
        }
        
        return {
            "raw_response": json.dumps(mock_json_response, indent=2),
            "structured_data": mock_json_response,
            "strategy_used": f"Mock{context_type.title()}Analysis"
        } 