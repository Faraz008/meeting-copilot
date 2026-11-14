import pytest

from copilot.llm.jsonutil import JSONParseError, extract_json


def test_extract_fenced_json():
    text = """```json
    {"action": "send draft", "priority": "high"}
    ```"""

    result = extract_json(text)

    assert result == {"action": "send draft", "priority": "high"}


def test_extract_json_with_surrounding_prose():
    text = """Here is the extracted information:

    {"action": "send draft", "priority": "high"}

    Let me know if you need anything else."""

    result = extract_json(text)

    assert result == {"action": "send draft", "priority": "high"}


def test_extract_json_with_trailing_comma():
    text = """{
        "action": "send draft",
        "priority": "high",
    }"""

    result = extract_json(text)

    assert result == {"action": "send draft", "priority": "high"}


def test_garbage_raises_json_parse_error():
    text = "This is not JSON and contains no JSON object."

    with pytest.raises(JSONParseError):
        extract_json(text)
