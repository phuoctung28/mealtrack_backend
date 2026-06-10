"""Guardrails for the async-only repository consolidation rollout."""

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
SRC_ROOT = PROJECT_ROOT / "src"

ALLOWED_SYNC_DB_IMPORT_FILES = set()

ALLOWED_REPOSITORY_TRANSACTION_FILES = {
    "src/infra/repositories/pgvector_meal_image_cache_repository_async.py",
}


def _python_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*.py") if "__pycache__" not in path.parts
    )


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports_sync_db_boundary(path: Path) -> bool:
    tree = _parse(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_names = {alias.name for alias in node.names}
            if module in {"src.infra.database.config", "src.infra.database.uow"}:
                return True
            if module == "sqlalchemy.orm" and "Session" in imported_names:
                return True
        if isinstance(node, ast.Import):
            if any(
                alias.name in {"src.infra.database.config", "src.infra.database.uow"}
                for alias in node.names
            ):
                return True
    return False


def _calls_transaction_boundary(path: Path) -> bool:
    tree = _parse(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"commit", "rollback"}:
                return True
    return False


def test_sync_db_runtime_imports_do_not_expand_during_transition() -> None:
    offenders = {
        _relative(path)
        for path in _python_files(SRC_ROOT)
        if _imports_sync_db_boundary(path)
        and _relative(path) not in {"src/infra/database/config.py"}
    }

    assert offenders == ALLOWED_SYNC_DB_IMPORT_FILES


def test_repository_transaction_boundary_allowlist_does_not_expand() -> None:
    repo_root = SRC_ROOT / "infra" / "repositories"
    offenders = {
        _relative(path)
        for path in _python_files(repo_root)
        if _calls_transaction_boundary(path)
    }

    assert offenders == ALLOWED_REPOSITORY_TRANSACTION_FILES


def test_orm_models_do_not_import_base_from_sync_config() -> None:
    offenders = []
    for path in _python_files(SRC_ROOT / "infra" / "database" / "models"):
        tree = _parse(path)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "src.infra.database.config"
            ):
                imported_names = {alias.name for alias in node.names}
                if "Base" in imported_names:
                    offenders.append(_relative(path))

    assert offenders == []


def test_tests_do_not_reintroduce_generic_sync_to_async_repo_wrapper() -> None:
    """Generic wrappers hide sync repositories behind awaitable methods."""
    forbidden = {
        "Async" + "SyncRepoWrapper",
        "Wraps a sync repository so every method is also " + "awaitable",
    }
    offenders: dict[str, list[str]] = {}
    for path in _python_files(PROJECT_ROOT / "tests"):
        text = path.read_text(encoding="utf-8")
        matches = [term for term in forbidden if term in text]
        if matches:
            offenders[_relative(path)] = matches

    assert offenders == {}


def test_legacy_sync_repositories_do_not_expose_async_compatibility_methods() -> None:
    offenders: dict[str, list[str]] = {}
    repo_root = SRC_ROOT / "infra" / "repositories"
    for path in _python_files(repo_root):
        if path.name.endswith("_async.py"):
            continue
        tree = _parse(path)
        async_defs = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
            and (
                node.name.endswith("_async") or node.name in {"get_async", "add_async"}
            )
        ]
        if async_defs:
            offenders[_relative(path)] = async_defs

    assert offenders == {}


def test_food_reference_request_dependencies_use_async_adapter() -> None:
    """Request-path food-reference services must not wire the sync singleton."""
    offenders: dict[str, list[str]] = {}
    forbidden = {
        "food_ref_repo=get_food_reference_repository(",
        "food_reference_repository=get_food_reference_repository(",
        "food_reference_repository import FoodReferenceRepository",
    }
    for path in _python_files(SRC_ROOT / "api"):
        text = path.read_text(encoding="utf-8")
        matches = [term for term in forbidden if term in text]
        if matches:
            offenders[_relative(path)] = matches

    assert offenders == {}


def test_meal_translation_dependency_uses_async_adapter() -> None:
    """Meal translation service wiring must not instantiate the sync repository."""
    path = SRC_ROOT / "api" / "base_dependencies.py"
    text = path.read_text(encoding="utf-8")

    assert "MealTranslationRepository()" not in text
    assert "get_async_meal_translation_repository()" in text


def test_promo_referral_runtime_handlers_use_uow_repositories() -> None:
    """Request/handler code should use AsyncUnitOfWork-owned repositories."""
    offenders: dict[str, list[str]] = {}
    forbidden = {
        "PromoCodeRepository(",
        "ReferralRepository(",
        "promo_code_repository import PromoCodeRepository",
        "referral_repository import ReferralRepository",
    }
    scanned_roots = [
        SRC_ROOT / "app",
        SRC_ROOT / "api",
        SRC_ROOT / "cron",
        SRC_ROOT / "infra" / "services",
    ]

    for root in scanned_roots:
        for path in _python_files(root):
            text = path.read_text(encoding="utf-8")
            matches = [term for term in forbidden if term in text]
            if matches:
                offenders[_relative(path)] = matches

    assert offenders == {}
