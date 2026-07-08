"""Quality-gate helpers for meal analysis graph state."""

from src.app.graphs.meal_analyze.state import MealAnalyzeGraphState

DEFAULT_GRAPH_VERSION = "v1"


def normalize_scan_mode(state: MealAnalyzeGraphState) -> str:
    """Return a supported scan mode for graph state."""
    scan_mode = state.get("scan_mode")
    if scan_mode == "food_label":
        return "food_label"
    return "meal_scan"
