"""Deterministic review gates for the translation evaluation fixture."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from src.domain.constants.languages import SUPPORTED_TRANSLATION_LANGUAGES
from src.infra.adapters.openai_translation_adapter import OpenAITranslationAdapter

FIXTURE_PATH = (
    Path(__file__).resolve().parents[4]
    / "tests/fixtures/translation/openai_translation_eval_fixture.json"
)
TOKEN_PATTERN = re.compile(r"\{[^{}]+\}|\d+(?:[.,]\d+)?")


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fixture_covers_the_supported_seven_locale_policy() -> None:
    fixture = _fixture()

    assert fixture["source_language"] == "en"
    assert set(fixture["locales"]) == set(SUPPORTED_TRANSLATION_LANGUAGES)
    assert len(fixture["locales"]) == 7
    assert len({case["id"] for case in fixture["cases"]}) == len(fixture["cases"])


@pytest.mark.parametrize("case_index", range(4))
def test_fixture_has_complete_non_empty_translations_and_preserves_tokens(
    case_index: int,
) -> None:
    case = _fixture()["cases"][case_index]
    translations = case["translations"]

    assert set(translations) == set(SUPPORTED_TRANSLATION_LANGUAGES)
    assert all(
        isinstance(value, str) and value.strip() for value in translations.values()
    )
    source_tokens = TOKEN_PATTERN.findall(case["source"])
    for translated in translations.values():
        assert Counter(TOKEN_PATTERN.findall(translated)) == Counter(source_tokens)


def test_fixture_translations_pass_adapter_invariant_guard() -> None:
    adapter = OpenAITranslationAdapter(provider=None, model="translation-model")

    for case in _fixture()["cases"]:
        for locale, translated in case["translations"].items():
            if locale == "en":
                continue
            assert adapter._safe_output(case["source"], translated, locale, "en"), (
                case["id"],
                locale,
            )


def test_active_repository_surfaces_contain_no_vendor_translation_residue() -> None:
    root = FIXTURE_PATH.parents[3]
    # Build the marker so this test does not match its own source text.
    marker = "d" + "ee" + "pl"
    excluded_prefixes = (
        root / "migrations",
        root / "docs/archive",
        root / "docs/journals",
        root / "plans",
        root / ".git",
        root / ".venv",
        root / ".pytest_cache",
        root / "src/mealtrack_backend.egg-info",
    )
    excluded_names = {"repomix-output.xml"}
    source_suffixes = {".py", ".md", ".toml", ".txt", ".lock", ".example"}
    hits: list[str] = []

    for path in root.rglob("*"):
        if (
            not path.is_file()
            or path.name in excluded_names
            or path.suffix not in source_suffixes
        ):
            continue
        if any(
            path == prefix or prefix in path.parents for prefix in excluded_prefixes
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        api_key_marker = "DEE" + "PL_API_KEY"
        if (
            marker in text.lower()
            or api_key_marker in text
            or "get_" + marker in text.lower()
        ):
            hits.append(str(path.relative_to(root)))

    assert hits == []
