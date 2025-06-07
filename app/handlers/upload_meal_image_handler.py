import asyncio
import logging
import uuid
from typing import Dict, Any, List

from fastapi import UploadFile

from app.services.meal_ingredient_service import MealIngredientService
from domain.ports.vision_ai_service_port import VisionAIServicePort
from domain.services.analysis_strategy import AnalysisStrategyFactory

logger = logging.getLogger(__name__)

class UploadMealImageHandler:
    """Handler for meal image upload and analysis operations."""
    
    def __init__(self, vision_ai_service: VisionAIServicePort, ingredient_service: MealIngredientService):
        self.vision_ai_service = vision_ai_service
        self.ingredient_service = ingredient_service
    
    async def handle_meal_upload(self, file: UploadFile) -> Dict[str, Any]:
        """Handle meal image upload and analysis."""
        await self._validate_image_file(file)
        
        meal_id = str(uuid.uuid4())
        image_bytes = await file.read()
        
        try:
            result = self.vision_ai_service.analyze(image_bytes)
            
            return {
                "meal_id": meal_id,
                "status": "success",
                "message": "Meal image analyzed successfully",
                "analysis": result["structured_data"],
                "confidence": result["structured_data"].get("confidence", 0.0),
                "raw_response": result.get("raw_response", "")
            }
        except Exception as e:
            logger.error(f"Failed to analyze meal image: {str(e)}")
            return {
                "meal_id": meal_id,
                "status": "error",
                "message": "Failed to analyze meal image",
                "error": str(e)
            }
    
    async def update_meal_macros(self, meal_id: str, portion_size: float, unit: str) -> Dict[str, Any]:
        """Update meal macros based on portion size."""
        # Return scaled response immediately
        scaled_response = self._calculate_immediate_scaling(portion_size, unit)
        
        # Start background analysis
        asyncio.create_task(self.analyze_meal_with_portion_background(meal_id, portion_size, unit))
        
        return {
            "meal_id": meal_id,
            "status": "analyzing",
            "message": "Calculating precise macros with AI analysis",
            "immediate_calculation": scaled_response,
            "note": "Final results will be available shortly"
        }
    
    async def add_ingredients_to_meal(self, meal_id: str, ingredients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add ingredients to meal and update macros."""
        # Store ingredients
        for ingredient_data in ingredients:
            self.ingredient_service.add_ingredient(meal_id, ingredient_data)
        
        # Return immediate response
        stored_ingredients = self.ingredient_service.get_ingredients_for_meal(meal_id)
        
        # Start background analysis
        asyncio.create_task(self.analyze_meal_with_ingredients_background(meal_id, stored_ingredients))
        
        return {
            "meal_id": meal_id,
            "status": "analyzing", 
            "message": "Ingredients added, calculating combined macros with AI",
            "ingredients_added": len(ingredients),
            "total_ingredients": len(stored_ingredients),
            "note": "Final macro calculations will be available shortly"
        }
    
    async def analyze_meal_with_portion_background(self, meal_id: str, portion_size: float, unit: str):
        """Background task for portion-aware analysis."""
        try:
            strategy = AnalysisStrategyFactory.create_portion_strategy(portion_size, unit)
            await self._analyze_meal_background_with_context(meal_id, strategy, "portion analysis")
        except Exception as e:
            logger.error(f"Background portion analysis failed for meal {meal_id}: {str(e)}")
    
    async def analyze_meal_with_ingredients_background(self, meal_id: str, ingredients: List[Dict[str, Any]]):
        """Background task for ingredient-aware analysis."""
        try:
            strategy = AnalysisStrategyFactory.create_ingredient_strategy(ingredients)
            await self._analyze_meal_background_with_context(meal_id, strategy, "ingredient analysis")
        except Exception as e:
            logger.error(f"Background ingredient analysis failed for meal {meal_id}: {str(e)}")
    
    async def _analyze_meal_background_with_context(self, meal_id: str, strategy, analysis_type: str):
        """Perform background analysis with context."""
        try:
            # Simulate image bytes (in real app, get from stored meal)
            mock_image_bytes = b"mock_image_data"
            
            result = self.vision_ai_service.analyze(mock_image_bytes, strategy)
            
            logger.info(f"Completed {analysis_type} for meal {meal_id}")
            logger.info(f"Strategy used: {result.get('strategy_used', 'unknown')}")
            logger.info(f"Confidence: {result['structured_data'].get('confidence', 0.0)}")
            
        except Exception as e:
            logger.error(f"Failed {analysis_type} for meal {meal_id}: {str(e)}")
    
    def _calculate_immediate_scaling(self, portion_size: float, unit: str) -> Dict[str, Any]:
        """Calculate immediate macro scaling."""
        base_macros = {"protein": 25.0, "carbs": 30.0, "fat": 12.0, "fiber": 8.0}
        base_calories = 350
        base_portion = 150.0
        
        ratio = portion_size / base_portion
        
        return {
            "portion_size": portion_size,
            "unit": unit,
            "scaling_ratio": round(ratio, 2),
            "estimated_calories": round(base_calories * ratio),
            "estimated_macros": {k: round(v * ratio, 1) for k, v in base_macros.items()},
            "note": "Estimates based on mathematical scaling. AI analysis in progress for precise values."
        }
    
    async def _validate_image_file(self, file: UploadFile):
        """Validate uploaded image file."""
        if not file.content_type or not file.content_type.startswith('image/'):
            raise ValueError("File must be an image")
        
        # Check file size (8MB limit)
        content = await file.read()
        if len(content) > 8 * 1024 * 1024:
            raise ValueError("File size exceeds 8MB limit")
        
        # Reset file pointer for later reading
        await file.seek(0) 