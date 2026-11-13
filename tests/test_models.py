import pytest
from pydantic import ValidationError

from copilot.models import ActionItem, Evidence, stable_id


def test_empty_evidence_is_rejected():
    with pytest.raises(ValidationError):
        ActionItem(
            title="Prepare project report",
            evidence=[],
        )


def test_blank_title_is_rejected():
    evidence = Evidence(
        turn_idx=0,
        quote="I will prepare the project report.",
    )

    with pytest.raises(ValidationError):
        ActionItem(
            title="   ",
            evidence=[evidence],
        )


def test_stable_id_is_consistent_across_calls():
    first_id = stable_id(
        kind="action",
        meeting_id="meeting-001",
        first_turn_idx=5,
    )

    second_id = stable_id(
        kind="action",
        meeting_id="meeting-001",
        first_turn_idx=5,
    )

    assert first_id == second_id


def test_stable_id_changes_with_meeting_or_position():
    original_id = stable_id("action", "meeting-001", 5)

    different_meeting_id = stable_id("action", "meeting-002", 5)
    different_position_id = stable_id("action", "meeting-001", 6)

    assert original_id != different_meeting_id
    assert original_id != different_position_id
