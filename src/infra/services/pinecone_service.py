"""
Pinecone Meal Nutrition Service

Integrates Pinecone vector search for ingredient lookup with nutrition scaling.
Based on the MVP implementation from my-python-repo/mvp/meal_nutrition.py
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional

from pinecone import Pinecone


@dataclass
class NutritionData:
    """Nutrition per serving"""
    calories: float = 0
    protein: float = 0
    fat: float = 0
    carbs: float = 0
    fiber: float = 0
    sugar: float = 0
    sodium: float = 0
    serving_size_g: float = 100

    def scale_to(self, grams: float) -> 'NutritionData':
        """Scale nutrition to specific amount in grams"""
        if self.serving_size_g == 0:
            return self
        factor = grams / self.serving_size_g
        return NutritionData(
            calories=self.calories * factor,
            protein=self.protein * factor,
            fat=self.fat * factor,
            carbs=self.carbs * factor,
            fiber=self.fiber * factor,
            sugar=self.sugar * factor,
            sodium=self.sodium * factor,
            serving_size_g=grams
        )


class PineconeNutritionService:
    """
    Service for searching ingredients and calculating nutrition using Pinecone.
    
    Memory optimization: Uses lazy loading for indexes to avoid upfront memory allocation.
    """

    def __init__(self, pinecone_api_key: Optional[str] = None):
        api_key = pinecone_api_key or os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY must be provided or set in environment")

        self.pc = Pinecone(api_key=api_key)
        # No encoder needed - use Pinecone inference API

        # Lazy load indexes (only connect when needed)
        self._ingredients_index = None
        self._usda_index = None
        self._indexes_initialized = False
    
    @property
    def ingredients_index(self):
        """Lazy load ingredients index."""
        if not self._indexes_initialized:
            self._init_indexes()
        return self._ingredients_index
    
    @property
    def usda_index(self):
        """Lazy load USDA index."""
        if not self._indexes_initialized:
            self._init_indexes()
        return self._usda_index
    
    def _init_indexes(self):
        """Initialize Pinecone indexes on first use."""
        if self._indexes_initialized:
            return
        
        # Connect to existing indexes
        try:
            self._ingredients_index = self.pc.Index("ingredients")
        except Exception:
            self._ingredients_index = None

        try:
            self._usda_index = self.pc.Index("usda")
        except Exception:
            self._usda_index = None

        if not self._ingredients_index and not self._usda_index:
            raise ValueError("No Pinecone indexes available. Ensure 'ingredients' or 'usda' index exists.")
        
        self._indexes_initialized = True

        # Unit conversion table
        self.unit_conversions = {
            'g': 1, 'gram': 1, 'grams': 1,
            'kg': 1000, 'oz': 28.35, 'lb': 453.59,
            'cup': 240, 'cups': 240,
            'tbsp': 15, 'tablespoon': 15,
            'tsp': 5, 'teaspoon': 5,
            'serving': 100
        }

    def _embed_text(
        self, texts: list[str], input_type: str = "query"
    ) -> list[list[float]]:
        """
        Generate embeddings using Pinecone Inference API.

        Args:
            texts: List of text strings to embed
            input_type: "query" for search queries, "passage" for documents

        Returns:
            List of embedding vectors (1024 dimensions each)
        """
        embeddings = self.pc.inference.embed(
            model="llama-text-embed-v2",
            inputs=texts,
            parameters={
                "input_type": input_type,
                "truncate": "END"
            }
        )
        return [e["values"] for e in embeddings]

    def search_ingredient(self, query: str) -> Optional[Dict]:
        """
        Search for ingredient in Pinecone indexes using vector similarity.
        Returns nutrition data per 100g if found.
        """
        best_result = None
        best_score = 0

        # Generate embedding for search query using Pinecone Inference API
        query_embedding = self._embed_text([query], input_type="query")[0]

        # Try ingredients index first (better per-100g data)
        if self.ingredients_index:
            try:
                results = self.ingredients_index.query(
                    vector=query_embedding,
                    top_k=1,
                    include_metadata=True
                )

                if results and 'matches' in results and results['matches']:
                    match = results['matches'][0]
                    if match['score'] > 0.35:
                        best_result = match
                        best_score = match['score']
            except Exception as e:
                print(f"Ingredients index query failed: {e}")

        # Try USDA if no good match
        if self.usda_index and best_score < 0.6:
            try:
                results = self.usda_index.query(
                    vector=query_embedding,
                    top_k=1,
                    include_metadata=True
                )

                if results and 'matches' in results and results['matches']:
                    if results['matches'][0]['score'] > best_score * 1.2:
                        best_result = results['matches'][0]
            except Exception as e:
                print(f"USDA index query failed: {e}")

        if best_result:
            metadata = best_result['metadata']
            return {
                'name': metadata.get('name', query),
                'score': best_result['score'],
                'calories': float(metadata.get('calories', 0)),
                'protein': float(metadata.get('protein', 0)),
                'fat': float(metadata.get('fat', 0)),
                'carbs': float(metadata.get('carbs', 0)),
                'fiber': float(metadata.get('fiber', 0)),
                'sugar': float(metadata.get('sugar', 0)),
                'sodium': float(metadata.get('sodium', 0)),
                'serving_size': metadata.get('serving_size', '100g')
            }

        return None

    def convert_to_grams(self, quantity: float, unit: str) -> float:
        """Convert quantity in any unit to grams"""
        unit_lower = unit.lower()
        conversion_factor = self.unit_conversions.get(unit_lower, 1)
        return quantity * conversion_factor

    def get_scaled_nutrition(
        self, 
        ingredient_name: str, 
        quantity: float, 
        unit: str
    ) -> Optional[NutritionData]:
        """
        Search for ingredient and return nutrition scaled to the specified portion.
        
        Args:
            ingredient_name: Name of the ingredient to search
            quantity: Amount of the ingredient
            unit: Unit of measurement (g, kg, cup, etc.)
            
        Returns:
            NutritionData scaled to the specified portion, or None if not found
        """
        # Search for ingredient
        result = self.search_ingredient(ingredient_name)
        if not result:
            return None

        # Create base nutrition (per 100g)
        base_nutrition = NutritionData(
            calories=result['calories'],
            protein=result['protein'],
            fat=result['fat'],
            carbs=result['carbs'],
            fiber=result['fiber'],
            sugar=result['sugar'],
            sodium=result['sodium'],
            serving_size_g=100
        )

        # Convert to grams and scale
        grams = self.convert_to_grams(quantity, unit)
        return base_nutrition.scale_to(grams)

    def calculate_total_nutrition(
        self, 
        ingredients: list[Dict]
    ) -> NutritionData:
        """
        Calculate total nutrition from a list of ingredients.
        
        Args:
            ingredients: List of dicts with 'name', 'quantity', 'unit'
            
        Returns:
            Total NutritionData summed across all ingredients
        """
        total = NutritionData(serving_size_g=0)

        for ingredient in ingredients:
            nutrition = self.get_scaled_nutrition(
                ingredient['name'],
                ingredient['quantity'],
                ingredient['unit']
            )
            
            if nutrition:
                total.calories += nutrition.calories
                total.protein += nutrition.protein
                total.fat += nutrition.fat
                total.carbs += nutrition.carbs
                total.fiber += nutrition.fiber
                total.sugar += nutrition.sugar
                total.sodium += nutrition.sodium
                total.serving_size_g += nutrition.serving_size_g

        return total


# Singleton instance (lazy initialization)
_pinecone_service_instance: Optional[PineconeNutritionService] = None


def get_pinecone_service() -> PineconeNutritionService:
    """Get or create singleton instance of PineconeNutritionService"""
    global _pinecone_service_instance
    if _pinecone_service_instance is None:
        _pinecone_service_instance = PineconeNutritionService()
    return _pinecone_service_instance
