import inspect


def test_all_5_strategies_return_vision_analysis_system_prompt():
    """All 5 meal analysis strategies must return SystemPrompts.VISION_ANALYSIS."""
    from src.domain.strategies.meal_analysis_strategy import (
        BasicAnalysisStrategy,
        PortionAwareAnalysisStrategy,
        IngredientAwareAnalysisStrategy,
        WeightAwareAnalysisStrategy,
        UserContextAwareAnalysisStrategy,
    )
    from src.infra.services.ai.prompts.system_prompts import SystemPrompts

    strategies = [
        BasicAnalysisStrategy(),
        PortionAwareAnalysisStrategy(350.0, "g"),
        IngredientAwareAnalysisStrategy([{"name": "rice", "quantity": 200, "unit": "g"}]),
        WeightAwareAnalysisStrategy(350.0),
        UserContextAwareAnalysisStrategy("I'm eating a chicken rice bowl"),
    ]
    for s in strategies:
        result = s.get_analysis_prompt()
        assert result == SystemPrompts.VISION_ANALYSIS, (
            f"{s.__class__.__name__}.get_analysis_prompt() must return SystemPrompts.VISION_ANALYSIS"
        )


def test_portion_aware_user_message_contains_portion_info():
    """PortionAwareAnalysisStrategy user message must include the portion size."""
    from src.domain.strategies.meal_analysis_strategy import PortionAwareAnalysisStrategy
    s = PortionAwareAnalysisStrategy(350.0, "g")
    msg = s.get_user_message()
    assert "350" in msg
    assert "g" in msg


def test_weight_aware_user_message_contains_weight():
    from src.domain.strategies.meal_analysis_strategy import WeightAwareAnalysisStrategy
    s = WeightAwareAnalysisStrategy(280.0)
    msg = s.get_user_message()
    assert "280" in msg


def test_scan_decomposition_rules_not_in_strategy_module():
    """SCAN_DECOMPOSITION_RULES and BASIC_SCAN_DECOMPOSITION_RULES must be removed
    from meal_analysis_strategy.py — they live in prompt_constants.py now."""
    from src.domain.strategies import meal_analysis_strategy
    source = inspect.getsource(meal_analysis_strategy)
    assert "SCAN_DECOMPOSITION_RULES = " not in source
    assert "BASIC_SCAN_DECOMPOSITION_RULES = " not in source


def test_vision_decomposition_rules_importable():
    """VISION_DECOMPOSITION_RULES must be importable from prompt_constants."""
    from src.domain.services.prompts.prompt_constants import VISION_DECOMPOSITION_RULES
    assert "DECOMPOSE" in VISION_DECOMPOSITION_RULES or "decompos" in VISION_DECOMPOSITION_RULES.lower()
