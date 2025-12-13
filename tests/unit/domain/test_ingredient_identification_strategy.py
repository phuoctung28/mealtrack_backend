"""
Unit tests for IngredientIdentificationStrategy.
"""
import pytest

from src.domain.strategies.meal_analysis_strategy import (
    IngredientIdentificationStrategy,
    AnalysisStrategyFactory,
)


class TestIngredientIdentificationStrategy:
    """Tests for IngredientIdentificationStrategy."""

    def test_get_analysis_prompt(self):
        """Test that analysis prompt is properly formatted."""
        strategy = IngredientIdentificationStrategy()
        prompt = strategy.get_analysis_prompt()

        # Should contain key elements
        assert "food ingredient" in prompt.lower()
        assert "json" in prompt.lower()
        assert "name" in prompt
        assert "confidence" in prompt
        assert "category" in prompt
        assert "vegetable" in prompt or "protein" in prompt

    def test_get_user_message(self):
        """Test that user message is appropriate."""
        strategy = IngredientIdentificationStrategy()
        message = strategy.get_user_message()

        assert "identify" in message.lower()
        assert "ingredient" in message.lower()

    def test_get_strategy_name(self):
        """Test strategy name is correct."""
        strategy = IngredientIdentificationStrategy()
        name = strategy.get_strategy_name()

        assert name == "IngredientIdentification"


class TestAnalysisStrategyFactory:
    """Tests for AnalysisStrategyFactory ingredient identification method."""

    def test_create_ingredient_identification_strategy(self):
        """Test factory creates correct strategy type."""
        strategy = AnalysisStrategyFactory.create_ingredient_identification_strategy()

        assert isinstance(strategy, IngredientIdentificationStrategy)

    def test_factory_returns_new_instance(self):
        """Test factory returns new instances each time."""
        strategy1 = AnalysisStrategyFactory.create_ingredient_identification_strategy()
        strategy2 = AnalysisStrategyFactory.create_ingredient_identification_strategy()

        assert strategy1 is not strategy2
