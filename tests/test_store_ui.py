from datetime import date

import pytest

from copilot import service
from copilot.models import ExtractionResult, Turn
from copilot.store import Store
from copilot.ui import helpers as H
from tests.helpers import seed


def test_edits_overlay_and_flags(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    seed(s, 2, approve=False)

    s.update_item("act_2", edits={"deadline": "2025-03-20"})

    it = {i["id"]: i for i in s.items("m1")}["act_2"]

    assert it["deadline"] == "2025-03-20"
    assert "unresolved_deadline" not in it["flags"]
    assert it["orig"]["deadline"] is None
    assert it["edited"] == ["deadline"]


def test_reextraction_keeps_review_state_and_marks_stale(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    seed(s, 2)

    s.update_item("act_1", edits={"owner": "Dan"})

    # An empty re-extraction should mark existing items as stale.
    only_first = ExtractionResult(action_items=[])
    s.save_extraction("m1", only_first)

    its = {i["id"]: i for i in s.items("m1")}

    assert its["act_1"]["stale"]
    assert its["act_1"]["state"] == "approved"
    assert its["act_1"]["owner"] == "Dan"
    assert its["act_2"]["stale"]


def test_approve_clean_skips_flagged(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    seed(s, 2, approve=False)

    assert service.approve_clean(s, "m1") == 1

    assert {i["id"]: i["state"] for i in s.items("m1")} == {
        "act_1": "approved",
        "act_2": "pending",
    }


def test_bad_edits_rejected(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    seed(s)

    for bad in (
        {"id": "x"},
        {"deadline": "tomorrow"},
        {"priority": "urgent"},
    ):
        with pytest.raises(ValueError):
            s.update_item("act_1", edits=bad)


def test_html_is_escaped_in_evidence():
    t = [
        Turn(
            idx=0,
            speaker="<b>X</b>",
            text="I will <script>alert(1)</script> send it",
        )
    ]

    out = H.evidence_html(t, [{"turn_idx": 0, "quote": "send it"}])

    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert "<mark>send it</mark>" in out


def test_md_escape_neutralizes_links_and_images():
    escaped = H.md_escape("![x](http://evil/x.png) [a](b)")

    assert "](" not in escaped.replace("\\](", "")


def test_compute_edits_drops_reverted_fields():
    orig = {
        "title": "A",
        "owner": "Priya",
        "deadline": "2025-03-14",
        "priority": "normal",
    }

    assert H.compute_edits(
        orig,
        {
            "title": "A",
            "owner": "Sam",
            "deadline": date(2025, 3, 14),
            "priority": "normal",
        },
    ) == {"owner": "Sam"}


def test_malicious_title_is_escaped():
    malicious = "<script>alert(1)</script> ![x](http://evil.example/image.png)"

    escaped = H.md_escape(malicious)

    assert "<script>" not in escaped
    assert "![x](" not in escaped
    assert "http://evil.example/image.png" not in escaped or "](http" not in escaped


def test_reextraction_preserves_approval_and_human_edits(tmp_path):
    from copilot.models import ActionItem, Evidence, ExtractionResult

    s = Store(tmp_path / "t.sqlite")
    seed(s, 2)

    # Human approves the item and changes its owner.
    s.update_item("act_1", edits={"owner": "Dan"})

    # Simulate a fresh extraction of the same transcript.
    reextracted = ExtractionResult(
        action_items=[
            ActionItem(
                id="act_1",
                title="Send pricing draft",
                owner="Priya",
                owner_raw="I",
                deadline=date(2025, 3, 14),
                deadline_raw="by Friday",
                confidence=0.9,
                evidence=[
                    Evidence(
                        turn_idx=0,
                        quote="I'll send the draft by Friday.",
                    )
                ],
            )
        ]
    )

    s.save_extraction("m1", reextracted)

    items = {i["id"]: i for i in s.items("m1")}
    item = items["act_1"]

    assert item["state"] == "approved"
    assert item["owner"] == "Dan"
    assert item["edited"] == ["owner"]
    assert item["stale"] is False

    # The item missing from the new extraction becomes stale.
    assert items["act_2"]["stale"] is True
    assert items["act_2"]["state"] == "approved"


def test_meeting_obj_missing_id_raises_key_error(tmp_path):
    s = Store(tmp_path / "t.sqlite")

    with pytest.raises(KeyError, match="missing"):
        s.meeting_obj("missing")


def test_save_extraction_disambiguates_duplicate_ids(tmp_path):
    from copilot.models import ActionItem, Evidence, ExtractionResult

    s = Store(tmp_path / "t.sqlite")
    seed(s, 0)

    first = ActionItem(
        id="duplicate",
        title="First task",
        owner="Priya",
        owner_raw="I",
        confidence=0.9,
        evidence=[Evidence(turn_idx=0, quote="I'll do the first task.")],
    )
    second = ActionItem(
        id="duplicate",
        title="Second task",
        owner="Sam",
        owner_raw="I",
        confidence=0.9,
        evidence=[Evidence(turn_idx=1, quote="I'll do the second task.")],
    )

    s.save_extraction("m1", ExtractionResult(action_items=[first, second]))

    items = s.items("m1", "action")
    assert {item["id"] for item in items} == {"duplicate", "duplicatex1"}
    assert {item["title"] for item in items} == {"First task", "Second task"}


def test_update_item_rejects_invalid_review_state(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    seed(s)

    with pytest.raises(ValueError, match="bad state"):
        s.update_item("act_1", state="completed")


def test_delete_meeting_removes_meeting_items_and_pushes(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    seed(s)

    s.record_push(
        "act_1",
        "notion",
        "page-123",
        "https://notion.so/page-123",
        "hash-123",
        "created",
    )
    s.record_push(
        "meeting:m1",
        "slack",
        "message-123",
        None,
        "hash-456",
        "created",
    )

    assert s.get_push("act_1", "notion") is not None
    assert s.get_push("meeting:m1", "slack") is not None

    s.delete_meeting("m1")

    assert s.get_meeting("m1") is None
    assert s.get_push("act_1", "notion") is None
    assert s.get_push("meeting:m1", "slack") is None
