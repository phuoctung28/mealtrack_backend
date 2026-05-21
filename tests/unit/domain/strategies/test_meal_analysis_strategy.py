import inspect


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
