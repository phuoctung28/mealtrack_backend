"""Purpose-to-model mapping, fallback chains, and temperature config for GeminiService."""

from enum import Enum


class ModelPurpose(Enum):
    """Purpose-based model selection."""

    MEAL_SCAN = "meal_scan"
    INGREDIENT_SCAN = "ingredient_scan"
    PARSE_TEXT = "parse_text"
    BARCODE = "barcode"
    MEAL_NAMES = "meal_names"
    RECIPE = "recipe"
    DISCOVERY = "discovery"
    GENERAL = "general"


FALLBACK_CHAINS: dict[ModelPurpose, list[str]] = {
    # ==========================================================================
    # VISION / SHORT STRUCTURED TASKS: Gemini Flash-Lite first → Flash fallback
    # ==========================================================================
    ModelPurpose.MEAL_SCAN: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.INGREDIENT_SCAN: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    # ==========================================================================
    # SHORT STRUCTURED TEXT: Gemini Flash-Lite first → Flash fallback
    # ==========================================================================
    ModelPurpose.PARSE_TEXT: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.BARCODE: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.MEAL_NAMES: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.DISCOVERY: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    ModelPurpose.GENERAL: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
    # ==========================================================================
    # RECIPE TASKS: Gemini Flash-Lite first → Flash fallback
    # ==========================================================================
    ModelPurpose.RECIPE: ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
}

# Temperature per purpose — lower = more deterministic (extraction); higher = creative
PURPOSE_TEMPERATURES: dict[ModelPurpose, float] = {
    ModelPurpose.GENERAL: 0.2,
    ModelPurpose.MEAL_NAMES: 0.7,
    ModelPurpose.RECIPE: 0.4,
    ModelPurpose.BARCODE: 0.1,
    ModelPurpose.MEAL_SCAN: 0.2,
    ModelPurpose.INGREDIENT_SCAN: 0.2,
    ModelPurpose.PARSE_TEXT: 0.2,
    ModelPurpose.DISCOVERY: 0.7,
}

# Purposes that disable thinking budget (extraction tasks needing raw structured output)
NO_THINKING_PURPOSES: frozenset[ModelPurpose] = frozenset(
    {ModelPurpose.RECIPE, ModelPurpose.BARCODE}
)
