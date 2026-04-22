from src.api.base_dependencies import get_gpt_parser
from src.domain.parsers.gpt_response_parser import GPTResponseParser


def test_get_gpt_parser_returns_parser_instance():
    parser = get_gpt_parser()
    assert isinstance(parser, GPTResponseParser)
