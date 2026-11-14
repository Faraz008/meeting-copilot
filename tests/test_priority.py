from datetime import date

import pytest

from copilot.resolve.priority import priority

BASE = date(2026, 11, 14)


@pytest.mark.parametrize(
    "text",
    [
        "This is urgent",
        "ASAP please",
        "This is a critical blocker",
        "P0 task",
        "P1 task",
        "Top priority",
        "High priority",
        "Do this immediately",
        "We need this right away",
    ],
)
def test_explicit_high_priority(text):
    assert priority(text, None, BASE) == "high"


@pytest.mark.parametrize(
    "text",
    [
        "Low priority",
        "Nice to have",
        "No rush",
        "Whenever you can",
        "When you get a chance",
        "Eventually",
        "Someday",
    ],
)
def test_explicit_low_priority(text):
    assert priority(text, None, BASE) == "low"


def test_deadline_today_is_high():
    assert priority("Finish the report", BASE, BASE) == "high"


def test_deadline_tomorrow_is_high():
    assert priority("Finish the report", date(2026, 11, 15), BASE) == "high"


def test_deadline_after_tomorrow_is_normal():
    assert priority("Finish the report", date(2026, 11, 16), BASE) == "normal"


def test_no_deadline_is_normal():
    assert priority("Finish the report", None, BASE) == "normal"


def test_explicit_high_overrides_explicit_low():
    assert priority("Urgent, but no rush", None, BASE) == "high"
