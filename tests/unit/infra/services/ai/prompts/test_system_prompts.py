def test_recipe_generation_prompt_exists():
    from src.infra.services.ai.prompts.system_prompts import SystemPrompts
    assert hasattr(SystemPrompts, "RECIPE_GENERATION")
    assert isinstance(SystemPrompts.RECIPE_GENERATION, str)
    assert len(SystemPrompts.RECIPE_GENERATION) > 1000  # at least ~1024 tokens worth


def test_recipe_generation_has_worked_examples():
    from src.infra.services.ai.prompts.system_prompts import SystemPrompts
    # Must have at least one worked example
    assert "WORKED EXAMPLE" in SystemPrompts.RECIPE_GENERATION or "example" in SystemPrompts.RECIPE_GENERATION.lower()
    # Must include the JSON structure
    assert "recipe_steps" in SystemPrompts.RECIPE_GENERATION
    assert "ingredients" in SystemPrompts.RECIPE_GENERATION
