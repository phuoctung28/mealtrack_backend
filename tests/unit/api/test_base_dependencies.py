from src.api.base_dependencies import get_gpt_parser
from src.domain.parsers.gpt_response_parser import GPTResponseParser


def test_get_parse_text_settings_reads_structured_reference_flag(monkeypatch):
    import src.api.base_dependencies as dependencies

    class _Settings:
        PARSE_TEXT_STRUCTURED_REFERENCE_ENABLED = True

    import src.infra.config.settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: _Settings())

    assert dependencies.get_parse_text_settings() == {
        "structured_reference_enabled": True
    }


def test_get_gpt_parser_returns_parser_instance():
    parser = get_gpt_parser()
    assert isinstance(parser, GPTResponseParser)
