import re
from datetime import date, time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from copilot.resolve.deadlines import resolve_deadline

W, FRI, SAT, JAN31, YE = "2025-03-12", "2025-03-14", "2025-03-15", "2025-01-31", "2025-12-30"
# (raw, base, expected_date, status, time, options)
CASES = [
    ("Friday", W, "2025-03-14", "resolved", None, None),
    ("by Friday", W, "2025-03-14", "resolved", None, None),
    ("this Friday", W, "2025-03-14", "resolved", None, None),
    ("next Friday", W, "2025-03-21", "ambiguous", None, ["2025-03-14", "2025-03-21"]),
    ("next Tuesday", W, "2025-03-18", "resolved", None, None),
    ("next Tuesday latest", W, "2025-03-18", "resolved", None, None),
    ("Friday", FRI, "2025-03-21", "ambiguous", None, ["2025-03-14", "2025-03-21"]),
    ("this Friday", FRI, "2025-03-14", "resolved", None, None),
    ("this Monday", W, "2025-03-17", "resolved", None, None),
    ("Friday next week", W, "2025-03-21", "resolved", None, None),
    ("tomorrow", W, "2025-03-13", "resolved", None, None),
    ("the day after tomorrow", W, "2025-03-14", "resolved", None, None),
    ("EOD", W, "2025-03-12", "resolved", time(17, 0), None),
    ("end of day", W, "2025-03-12", "resolved", time(17, 0), None),
    ("EOD tomorrow", W, "2025-03-13", "resolved", time(17, 0), None),
    ("tomorrow at 3pm", W, "2025-03-13", "resolved", time(15, 0), None),
    ("Monday at 10am", W, "2025-03-17", "resolved", time(10, 0), None),
    ("end of day Friday", W, "2025-03-14", "resolved", time(17, 0), None),
    ("end of the week", W, "2025-03-14", "resolved", None, None),
    ("end of next week", W, "2025-03-21", "resolved", None, None),
    ("EOW", SAT, "2025-03-21", "resolved", None, None),
    ("end of the month", W, "2025-03-31", "resolved", None, None),
    ("end of the month", JAN31, "2025-01-31", "resolved", None, None),
    ("end of next month", W, "2025-04-30", "resolved", None, None),
    ("end of the quarter", W, "2025-03-31", "resolved", None, None),
    ("end of March", W, "2025-03-31", "resolved", None, None),
    ("end of the year", YE, "2025-12-31", "resolved", None, None),
    ("in two weeks", W, "2025-03-26", "resolved", None, None),
    ("in two weeks", YE, "2026-01-13", "resolved", None, None),
    ("in 3 days", W, "2025-03-15", "resolved", None, None),
    ("in 3 business days", W, "2025-03-17", "resolved", None, None),
    ("a couple of days", W, "2025-03-14", "resolved", None, None),
    ("in a month", JAN31, "2025-02-28", "resolved", None, None),
    ("next week", W, "2025-03-21", "ambiguous", None, ["2025-03-17", "2025-03-21"]),
    ("next month", JAN31, "2025-02-28", "ambiguous", None, ["2025-02-01", "2025-02-28"]),
    ("tomorrow", YE, "2025-12-31", "resolved", None, None),
    ("next Friday", YE, "2026-01-09", "ambiguous", None, ["2026-01-02", "2026-01-09"]),
    ("March 28th", W, "2025-03-28", "resolved", None, None),
    ("28th of March", W, "2025-03-28", "resolved", None, None),
    ("January 5th", YE, "2026-01-05", "resolved", None, None),
    ("the 15th", W, "2025-03-15", "resolved", None, None),
    ("the 10th", W, "2025-04-10", "resolved", None, None),
    ("2025-04-01", W, "2025-04-01", "resolved", None, None),
    ("3/28", W, "2025-03-28", "resolved", None, None),
    ("5/6", W, "2025-06-05", "ambiguous", None, ["2025-05-06", "2025-06-05"]),
    ("before the release", W, None, "unresolvable", None, None),
    ("ASAP", W, None, "unresolvable", None, None),
    ("when Dan approves", W, None, "unresolvable", None, None),
    ("a few days", W, None, "unresolvable", None, None),
    ("whenever", W, None, "unresolvable", None, None),
]


@pytest.mark.parametrize("raw,base,exp,status,tm,opts", CASES)
def test_resolve(raw, base, exp, status, tm, opts):
    r = resolve_deadline(raw, date.fromisoformat(base))
    assert r.resolved_date == (date.fromisoformat(exp) if exp else None), r
    assert r.status == status
    assert r.resolved_time == tm
    if opts is not None:
        assert r.options == [date.fromisoformat(o) for o in opts]


def test_mdy_order_changes_primary():
    r = resolve_deadline("5/6", date(2025, 3, 12), "MDY")
    assert r.resolved_date == date(2025, 5, 6)
    assert r.status == "ambiguous"


def test_never_raises_on_garbage():
    inputs = [
        "",
        "???",
        "31st of February",
        "99/99",
        "🙂",
    ]
    for s in inputs:
        result = resolve_deadline(s, date(2025, 3, 12))
        assert result.status in {
            "resolved",
            "ambiguous",
            "unresolvable",
        }


@given(raw=st.text(max_size=100))
@settings(max_examples=500)
def test_random_strings_never_raise_and_dates_are_not_in_past(raw):
    base = date(2025, 3, 12)

    result = resolve_deadline(raw, base)

    if result.resolved_date is None:
        return

    is_explicit_iso = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw.strip()))

    if is_explicit_iso:
        try:
            date.fromisoformat(raw.strip())
            return
        except ValueError:
            pass

    assert result.resolved_date >= base, (
        f"Unexpected past deadline: raw={raw!r}, base={base}, result={result}"
    )
