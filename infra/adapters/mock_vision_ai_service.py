from typing import Dict, Any, List
import json
import uuid
import logging

from domain.ports.vision_ai_service_port import VisionAIServicePort

logger = logging.getLogger(__name__)

class MockVisionAIService(VisionAIServicePort):
    """
    Mock implementation of VisionAIServicePort for testing and development.
    
    Returns realistic mock responses without requiring external dependencies.
    """
    
    def __init__(self):
        logger.info("Using MockVisionAIService - no external AI dependencies required")
    
    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """Mock image analysis with basic meal data."""
        return self._generate_mock_response("basic")
    
    def analyze_with_portion_context(self, image_bytes: bytes, portion_size: float, unit: str) -> Dict[str, Any]:
        """Mock analysis with portion context."""
        response = self._generate_mock_response("portion")
        
        # Adjust response based on portion size
        structured_data = response["structured_data"]
        ratio = portion_size / 150.0  # Assume 150g baseline
        
        # Scale nutrition values
        for food in structured_data["foods"]:
            food["quantity"] = round(food["quantity"] * ratio, 1)
            food["calories"] = round(food["calories"] * ratio)
            for macro in food["macros"]:
                food["macros"][macro] = round(food["macros"][macro] * ratio, 1)
        
        structured_data["total_calories"] = round(structured_data["total_calories"] * ratio)
        structured_data["portion_adjustment"] = f"Adjusted for {portion_size} {unit}"
        
        return response
    
    def analyze_with_ingredients_context(self, image_bytes: bytes, ingredients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock analysis with ingredients context."""
        response = self._generate_mock_response("ingredients")
        
        # Calculate totals based on provided ingredients
        total_calories = sum(ing.get("calories", 0) for ing in ingredients)
        total_protein = sum(ing.get("macros", {}).get("protein", 0) for ing in ingredients)
        total_carbs = sum(ing.get("macros", {}).get("carbs", 0) for ing in ingredients)
        total_fat = sum(ing.get("macros", {}).get("fat", 0) for ing in ingredients)
        total_fiber = sum(ing.get("macros", {}).get("fiber", 0) for ing in ingredients)
        
        # Update response with ingredient-based calculations
        structured_data = response["structured_data"]
        structured_data["total_calories"] = total_calories
        structured_data["confidence"] = 0.95  # Higher confidence with known ingredients
        structured_data["ingredient_based"] = True
        structured_data["combined_nutrition"] = "Calculated based on provided ingredients"
        
        # Replace foods with combined nutrition
        structured_data["foods"] = [{
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
        
        return response
    
    def analyze_with_weight_context(self, image_bytes: bytes, weight_grams: float) -> Dict[str, Any]:
        """Mock analysis with weight context."""
        response = self._generate_mock_response("weight")
        
        # Adjust response based on target weight
        structured_data = response["structured_data"]
        base_weight = 300.0  # Assume base weight of 300g
        ratio = weight_grams / base_weight
        
        # Scale nutrition values to match target weight
        for food in structured_data["foods"]:
            food["quantity"] = round(food["quantity"] * ratio, 1)
            food["calories"] = round(food["calories"] * ratio)
            for macro in food["macros"]:
                food["macros"][macro] = round(food["macros"][macro] * ratio, 1)
        
        structured_data["total_calories"] = round(structured_data["total_calories"] * ratio)
        structured_data["weight_adjustment"] = f"Adjusted for {weight_grams}g total weight"
        structured_data["confidence"] = 0.88  # Good confidence with weight context
        
        return response
    
    def _generate_mock_response(self, context_type: str = "basic") -> Dict[str, Any]:
        """Generate a realistic mock response."""
        
        # Mock food items based on common meals
        foods = [
            {
                "name": "Grilled Chicken Breast",
                "quantity": 120.0,
                "unit": "g",
                "calories": 200,
                "macros": {
                    "protein": 37.2,
                    "carbs": 0.0,
                    "fat": 4.3,
                    "fiber": 0.0
                }
            },
            {
                "name": "Brown Rice",
                "quantity": 150.0,
                "unit": "g",
                "calories": 195,
                "macros": {
                    "protein": 4.5,
                    "carbs": 40.0,
                    "fat": 1.5,
                    "fiber": 3.5
                }
            },
            {
                "name": "Steamed Broccoli",
                "quantity": 100.0,
                "unit": "g",
                "calories": 35,
                "macros": {
                    "protein": 3.7,
                    "carbs": 6.8,
                    "fat": 0.4,
                    "fiber": 2.6
                }
            }
        ]
        
        total_calories = sum(food["calories"] for food in foods)
        
        # Vary confidence based on context
        confidence_map = {
            "basic": 0.8,
            "portion": 0.85,
            "ingredients": 0.95,
            "weight": 0.88
        }
        
        mock_json_response = {
            "foods": foods,
            "total_calories": total_calories,
            "confidence": confidence_map.get(context_type, 0.8),
            "analysis_id": str(uuid.uuid4()),
            "mock_response": True
        }
        
        # Format as the expected response structure
        mock_raw_response = json.dumps(mock_json_response, indent=2)
        
        return {
            "raw_response": mock_raw_response,
            "structured_data": mock_json_response,
            "strategy_used": f"Mock{context_type.title()}Analysis"
        } 