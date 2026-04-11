import json

from src.infra.services.ai.parsers.ai_response_parser import AIResponseParser


def test_parse_response_plain_text_fallback():
    r = AIResponseParser.parse_response("hello")
    assert r["message"] == "hello"
    assert r["follow_ups"] == []
    assert r["structured_data"] is None


def test_parse_response_json_object():
    payload = {
        "message": "hi",
        "follow_ups": [{"text": "q1"}, "bad", {"id": "x", "text": "q2", "type": "choice"}],
        "meals": [{"name": "Meal", "ingredients": ["a"]}],
    }
    r = AIResponseParser.parse_response(json.dumps(payload))
    assert r["message"] == "hi"
    assert len(r["follow_ups"]) == 2
    assert r["follow_ups"][0]["id"] == "followup_0"
    assert r["follow_ups"][1]["id"] == "x"
    assert r["structured_data"]["meals"][0]["name"] == "Meal"


def test_parse_response_json_markdown_fence():
    content = "```json\n" + json.dumps({"message": "ok", "recipes": [{"x": 1}]}) + "\n```"
    r = AIResponseParser.parse_response(content)
    assert r["message"] == "ok"
    assert r["structured_data"]["recipes"] == [{"x": 1}]


def test_parse_response_structured_data_none_when_empty():
    r = AIResponseParser.parse_response(json.dumps({"message": "ok"}))
    assert r["structured_data"] is None


def test_validate_meals_defaults_and_filters_non_dict():
    parsed = {"meals": ["bad", {"name": "A"}]}
    r = AIResponseParser.parse_response(json.dumps(parsed))
    meals = r["structured_data"]["meals"]
    assert len(meals) == 1
    assert meals[0]["name"] == "A"
    assert meals[0]["difficulty"] == "medium"
    assert meals[0]["cook_time"] == "Unknown"


def test_is_json_response_detects_json_and_code_fence():
    assert AIResponseParser.is_json_response('{"a": 1}') is True
    assert AIResponseParser.is_json_response("```json\n{}\n```") is True
    assert AIResponseParser.is_json_response("{not json}") is False

