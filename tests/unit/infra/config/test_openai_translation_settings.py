from src.infra.config.settings import Settings


def test_translation_settings_have_safe_defaults():
    settings = Settings(_env_file=None)
    assert settings.OPENAI_TRANSLATION_MODEL == settings.OPENAI_TEXT_MODEL
    assert settings.OPENAI_TRANSLATION_TIMEOUT_SECONDS == 8.0

