"""
Service for searching recipes in Pinecone index.
Enables fast meal suggestion retrieval via semantic search.
"""
import json
import logging
from typing import List, Optional

from src.domain.ports.recipe_search_port import (
    RecipeSearchPort,
    RecipeSearchCriteria,
    RecipeSearchResult
)

logger = logging.getLogger(__name__)


class RecipeSearchService:
    """Searches recipe index for meal suggestions using injected search port."""

    def __init__(self, search_port: Optional[RecipeSearchPort] = None):
        """Initialize with optional search port (dependency injection)."""
        self._search_port = search_port

    def search_recipes(
        self,
        criteria: RecipeSearchCriteria,
        limit: int = 10
    ) -> List[RecipeSearchResult]:
        """
        Search for recipes matching criteria using injected port.

        Args:
            criteria: Search criteria
            limit: Number of results to return

        Returns:
            List of matching recipes, sorted by relevance
        """
        # Use injected search port or get default
        if not self._search_port:
            # Lazy import to avoid circular dependency
            from src.infra.services.pinecone_recipe_search_adapter import PineconeRecipeSearchAdapter
            try:
                self._search_port = PineconeRecipeSearchAdapter()
            except Exception as e:
                logger.warning(f"Failed to initialize recipe search adapter: {e}")
                return []
        
        return self._search_port.search_recipes(criteria, limit)
    
    def get_recipe_by_id(self, recipe_id: str) -> Optional[RecipeSearchResult]:
        """
        Get a specific recipe by ID.
        
        Args:
            recipe_id: The recipe ID
            
        Returns:
            Recipe if found, None otherwise
        """
        # Use injected search port or get default
        if not self._search_port:
            # Lazy import to avoid circular dependency
            from src.infra.services.pinecone_recipe_search_adapter import PineconeRecipeSearchAdapter
            try:
                self._search_port = PineconeRecipeSearchAdapter()
            except Exception as e:
                logger.warning(f"Failed to initialize recipe search adapter: {e}")
                return None
        
        return self._search_port.get_recipe_by_id(recipe_id)
