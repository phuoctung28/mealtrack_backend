import logging
import os
from typing import Optional, Dict, Any, List

import requests
from dotenv import load_dotenv

from domain.model.macros import Macros
from domain.model.nutrition import FoodItem
from domain.ports.food_database_port import FoodDatabasePort

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class USDAFoodDatabase(FoodDatabasePort):
    """
    USDA Food Database adapter for food lookup.
    
    Implements US-3.1 - Look up each food in a composition DB for more accurate results.
    """
    
    def __init__(self):
        """Initialize USDA Food Database client."""
        self.api_key = os.getenv("USDA_API_KEY")
        self.base_url = "https://api.nal.usda.gov/fdc/v1"
        
        # For demo purposes, we'll use a mock database if no API key
        self.use_mock = not self.api_key
        
        if self.use_mock:
            logger.info("Using mock food database (no USDA API key found)")
        else:
            logger.info("Using USDA Food Database API")
    
    def lookup(self, food_name: str, quantity: float, unit: str) -> Optional[FoodItem]:
        """
        Look up nutritional information for a food item.
        
        Args:
            food_name: Name of the food
            quantity: Quantity of the food
            unit: Unit of measurement (e.g., "g", "oz", "serving")
            
        Returns:
            FoodItem with standardized nutritional data if found, None otherwise
        """
        logger.info(f"Looking up food: {food_name} ({quantity} {unit})")
        
        if self.use_mock:
            return self._mock_lookup(food_name, quantity, unit)
        
        try:
            # Search for the food item
            search_results = self._search_food(food_name)
            
            if not search_results:
                logger.warning(f"No results found for: {food_name}")
                return None
            
            # Get the first result (most relevant)
            food_item = search_results[0]
            fdc_id = food_item.get("fdcId")
            
            if not fdc_id:
                logger.warning(f"No FDC ID found for: {food_name}")
                return None
            
            # Get detailed nutrition information
            nutrition_data = self._get_food_details(fdc_id)
            
            if not nutrition_data:
                logger.warning(f"No nutrition data found for FDC ID: {fdc_id}")
                return None
            
            # Convert to domain model
            return self._convert_to_food_item(nutrition_data, food_name, quantity, unit)
            
        except Exception as e:
            logger.error(f"Error looking up food {food_name}: {str(e)}")
            return None
    
    def lookup_batch(self, food_items: List[Dict[str, Any]]) -> Dict[str, Optional[FoodItem]]:
        """
        Look up nutritional information for multiple food items.
        
        Args:
            food_items: List of dictionaries with food name, quantity, and unit
            
        Returns:
            Dictionary mapping food names to FoodItems (or None if not found)
        """
        results = {}
        
        for item in food_items:
            food_name = item.get("name", "")
            quantity = item.get("quantity", 0)
            unit = item.get("unit", "g")
            
            result = self.lookup(food_name, quantity, unit)
            results[food_name] = result
            
        return results
    
    def _search_food(self, food_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for food items by name."""
        if not self.api_key:
            return []
        
        search_url = f"{self.base_url}/foods/search"
        params = {
            "query": food_name,
            "dataType": ["Foundation", "SR Legacy"],
            "pageSize": max_results,
            "api_key": self.api_key
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get("foods", [])
    
    def _get_food_details(self, fdc_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed nutrition information for a food item."""
        if not self.api_key:
            return None
        
        details_url = f"{self.base_url}/food/{fdc_id}"
        params = {"api_key": self.api_key}
        
        response = requests.get(details_url, params=params, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    def _convert_to_food_item(self, nutrition_data: Dict[str, Any], 
                             food_name: str, quantity: float, unit: str) -> Optional[FoodItem]:
        """Convert USDA nutrition data to domain FoodItem."""
        try:
            nutrients = nutrition_data.get("foodNutrients", [])
            
            # Map USDA nutrient IDs to our values
            nutrient_map = {
                1008: "calories",      # Energy (kcal)
                1003: "protein",       # Protein
                1005: "carbs",         # Total carbohydrates
                1004: "fat",           # Total fat
                1079: "fiber"          # Fiber
            }
            
            nutrition_values = {}
            
            # Extract nutrition values
            for nutrient in nutrients:
                nutrient_id = nutrient.get("nutrient", {}).get("id")
                value = nutrient.get("amount", 0)
                
                if nutrient_id in nutrient_map:
                    nutrition_values[nutrient_map[nutrient_id]] = float(value)
            
            # Default values if not found
            calories = nutrition_values.get("calories", 0)
            protein = nutrition_values.get("protein", 0)
            carbs = nutrition_values.get("carbs", 0)
            fat = nutrition_values.get("fat", 0)
            fiber = nutrition_values.get("fiber")
            
            # Adjust for quantity (USDA data is per 100g)
            scale_factor = self._get_scale_factor(quantity, unit)
            
            calories *= scale_factor
            protein *= scale_factor
            carbs *= scale_factor
            fat *= scale_factor
            if fiber is not None:
                fiber *= scale_factor
            
            # Create domain objects
            macros = Macros(
                protein=round(protein, 1),
                carbs=round(carbs, 1),
                fat=round(fat, 1),
                fiber=round(fiber, 1) if fiber is not None else None
            )
            
            food_item = FoodItem(
                name=food_name,
                quantity=quantity,
                unit=unit,
                calories=round(calories, 1),
                macros=macros,
                micros=None,  # Not implemented yet
                confidence=0.9  # High confidence for database lookup
            )
            
            logger.info(f"Successfully converted food item: {food_name}")
            return food_item
            
        except Exception as e:
            logger.error(f"Error converting nutrition data for {food_name}: {str(e)}")
            return None
    
    def _get_scale_factor(self, quantity: float, unit: str) -> float:
        """Get scale factor to convert from 100g base to actual quantity."""
        # Simple unit conversion - in real implementation would be more comprehensive
        unit_to_grams = {
            "g": 1.0,
            "kg": 1000.0,
            "oz": 28.35,
            "lb": 453.6,
            "cup": 240.0,  # Approximate for liquid
            "tbsp": 15.0,
            "tsp": 5.0,
            "serving": 100.0  # Default serving size
        }
        
        grams = quantity * unit_to_grams.get(unit.lower(), 100.0)
        return grams / 100.0  # USDA data is per 100g
    
    def _mock_lookup(self, food_name: str, quantity: float, unit: str) -> Optional[FoodItem]:
        """Mock food database for development/testing."""
        # Mock database with common foods
        mock_foods = {
            "chicken breast": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "fiber": 0},
            "grilled chicken": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "fiber": 0},
            "brown rice": {"calories": 112, "protein": 2.6, "carbs": 23, "fat": 0.9, "fiber": 1.8},
            "white rice": {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3, "fiber": 0.4},
            "broccoli": {"calories": 34, "protein": 2.8, "carbs": 7, "fat": 0.4, "fiber": 2.6},
            "salmon": {"calories": 208, "protein": 22, "carbs": 0, "fat": 12, "fiber": 0},
            "eggs": {"calories": 155, "protein": 13, "carbs": 1.1, "fat": 11, "fiber": 0},
            "avocado": {"calories": 160, "protein": 2, "carbs": 9, "fat": 15, "fiber": 7},
            "banana": {"calories": 89, "protein": 1.1, "carbs": 23, "fat": 0.3, "fiber": 2.6},
            "spinach": {"calories": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4, "fiber": 2.2}
        }
        
        # Simple fuzzy matching
        food_key = None
        for key in mock_foods.keys():
            if key.lower() in food_name.lower() or food_name.lower() in key.lower():
                food_key = key
                break
        
        if not food_key:
            logger.info(f"No mock data found for: {food_name}")
            return None
        
        data = mock_foods[food_key]
        scale_factor = self._get_scale_factor(quantity, unit)
        
        # Scale nutrition data
        calories = data["calories"] * scale_factor
        protein = data["protein"] * scale_factor
        carbs = data["carbs"] * scale_factor
        fat = data["fat"] * scale_factor
        fiber = data["fiber"] * scale_factor if data["fiber"] > 0 else None
        
        macros = Macros(
            protein=round(protein, 1),
            carbs=round(carbs, 1),
            fat=round(fat, 1),
            fiber=round(fiber, 1) if fiber is not None else None
        )
        
        food_item = FoodItem(
            name=food_name,
            quantity=quantity,
            unit=unit,
            calories=round(calories, 1),
            macros=macros,
            micros=None,
            confidence=0.8  # Lower confidence for mock data
        )
        
        logger.info(f"Mock lookup successful for: {food_name}")
        return food_item 