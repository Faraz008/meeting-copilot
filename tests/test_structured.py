import json

import pytest

from copilot.extract.raw_models import RawExtraction
from copilot.extract.structured import OutputTruncated, StructuredFailure, generate_validated
from copilot.llm.router import Router
from tests.fakes import FakeProvider

M = [
    {
        "role": "user",
        "content": "x",
    }
]

GOOD = json.dumps(
    {
        "action_items": [
            {
                "title": "Do thing",
                "evidence": [
                    {
                        "turn_idx": 0,
                        "quote": "do the thing",
                    }
                ],
            }
        ]
    }
)


def router(*provs):
    return Router(list(provs), sleep=lambda s: None)


def test_repair_succeeds_on_same_provider():
    a = FakeProvider("a", ["not json at all", GOOD])
    obj, att = generate_validated(router(a), M, RawExtraction)
    assert len(obj.action_items) == 1
    assert [x.kind for x in att] == ["invalid_json", "ok"] and att[-1].repaired
    assert "invalid" in a.calls[1][-1]["content"]  # error was fed back


def test_schema_error_then_fallback_provider():
    bad = json.dumps({"action_items": [{"title": "x"}]})
    a = FakeProvider("a", [bad, bad])
    b = FakeProvider("b", [GOOD])
    obj, att = generate_validated(router(a, b), M, RawExtraction)
    assert [x.provider for x in att] == ["a", "a", "b"] and att[0].kind == "schema"


def test_everything_fails_is_loud():
    with pytest.raises(StructuredFailure):
        generate_validated(router(FakeProvider("a", ["x", "y"])), M, RawExtraction)


def test_truncation_raises():
    fake = FakeProvider(
        "a",
        [
            ('{"action_items": [', "length"),
        ],
    )

    test_router = router(fake)

    with pytest.raises(OutputTruncated):
        generate_validated(
            test_router,
            M,
            RawExtraction,
        )
