from src.infra.services.ai.openai_translation_failures import (
    classify_translation_failure,
)


def test_failure_classifier_returns_bounded_categories_without_error_text():
    failure = classify_translation_failure(TimeoutError("secret prompt payload"))
    assert failure.category == "timeout"
    assert failure.error_code == "timeout"
    assert "secret" not in failure.__repr__()

