from copilot.models import ActionItem, Evidence, ExtractionResult, Turn
from copilot.privacy.pii import Redactor


def test_redacts_identifiers_but_not_dates_times_or_names():
    r = Redactor()
    out = r.redact_text(
        "Priya: mail me at priya.s@corp.in or +91 98765 43210,"
        "due 2025-03-14 at 10:30,"
        "card 4111 1111 1111 1111, PAN ABCDE1234F,"
        "see https://x.io/a?b=1 from 10.0.0.12"
    )
    for leaked in ("priya.s@corp.in", "98765", "4111", "ABCDE1234F", "https://x.io", "10.0.0.12"):
        assert leaked not in out
    assert "Priya" in out and "2025-03-14" in out and "10:30" in out


def test_non_luhn_number_is_left_alone():
    assert Redactor().redact_text("order 1234 5678 9012 3456") == "order 1234 5678 9012 3456"


def test_same_value_same_token_and_roundtrip_through_result():
    r = Redactor()
    t = r.redact_turns([Turn(idx=0, speaker="A", text="Send it to a@b.com, yes a@b.com")])[0].text
    assert t.count("[EMAIL_1]") == 2 and "[EMAIL_2]" not in t
    res = ExtractionResult(
        action_items=[
            ActionItem(
                id="act_1",
                title="Email [EMAIL_1] the plan",
                evidence=[Evidence(turn_idx=0, quote="Send it to [EMAIL_1]")],
            )
        ]
    )
    back = r.restore_result(res)
    assert back.action_items[0].title == "Email a@b.com the plan"
    assert "a@b.com" in back.action_items[0].evidence[0].quote


def test_end_to_end_cloud_prompt_never_contains_pii(tmp_path):
    import json
    from datetime import date

    from copilot.extract.safe import run_safe
    from copilot.llm.router import Router
    from tests.fakes import ConstProvider

    p = ConstProvider(
        "c",
        json.dumps(
            {
                "action_items": [],
                "decisions": [],
                "open_questions": [],
                "follow_ups": [],
            }
        ),
    )

    raw = "\n".join(
        (
            f"Ana: my number is 9876543210 and mail is "
            f"ana@corp.in so please plan item {i} for the release"
        )
        for i in range(12)
    )
    prompts = []
    orig = p.complete
    p.complete = lambda m, **k: (prompts.append(str(m)), orig(m, **k))[1]
    res = run_safe(
        raw,
        Router([p], sleep=lambda s: None),
        meeting_id="t",
        meeting_date=date(2025, 3, 12),
        redactor=Redactor(),
    )
    assert prompts and not any("9876543210" in x or "ana@corp.in" in x for x in prompts)
    assert res.report["redactions"]["EMAIL"] == 1
