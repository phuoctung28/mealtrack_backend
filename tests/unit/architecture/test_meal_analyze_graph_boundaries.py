"""Architecture guardrails for the meal image analysis graph."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOMAIN_ROOT = PROJECT_ROOT / "src" / "domain"
GRAPH_ROOT = PROJECT_ROOT / "src" / "app" / "graphs" / "meal_analyze"
APP_ROOT = PROJECT_ROOT / "src" / "app"

FORBIDDEN_GRAPH_IMPORTS = (
    "import openai",
    "from openai",
    "import langchain_openai",
    "from langchain_openai",
    "import langchain_cloudflare",
    "from langchain_cloudflare",
    "import sentry_sdk",
    "from sentry_sdk",
    "import sqlalchemy",
    "from sqlalchemy",
)


def _python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and path.name != "__init__.py"
    ]


def test_domain_layer_does_not_import_langgraph():
    offenders = []
    for path in _python_files(DOMAIN_ROOT):
        text = path.read_text(encoding="utf-8")
        if "langgraph" in text:
            offenders.append(path.relative_to(PROJECT_ROOT).as_posix())

    assert offenders == []


def test_meal_analyze_graph_does_not_import_provider_sdks_or_sql():
    offenders = []
    for path in _python_files(GRAPH_ROOT):
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_GRAPH_IMPORTS:
            if forbidden in text:
                offenders.append(
                    f"{path.relative_to(PROJECT_ROOT).as_posix()}: {forbidden}"
                )

    assert offenders == []


def test_application_layer_does_not_import_api_services():
    offenders = []
    for path in _python_files(APP_ROOT):
        text = path.read_text(encoding="utf-8")
        if "src.api.services" in text:
            offenders.append(path.relative_to(PROJECT_ROOT).as_posix())

    assert offenders == []
