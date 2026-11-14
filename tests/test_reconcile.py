from copilot.extract.raw_models import ActionCand, RawEvidence
from copilot.extract.reconcile import (
    apply_supersession,
    dedupe,
    merge_competing,
    same_commitment,
)
from copilot.models import Flag


def action(
    title,
    turn,
    quote,
    *,
    owner_raw="I",
    owner=None,
    deadline=None,
    status="committed",
    uid=1,
    supersedes_hint=None,
):
    return ActionCand(
        title=title,
        owner_raw=owner_raw,
        owner_turn_idx=turn,
        owner=owner,
        deadline_raw=deadline,
        status=status,
        confidence="high",
        evidence=[RawEvidence(turn_idx=turn, quote=quote)],
        uid=uid,
        supersedes_hint=supersedes_hint,
    )


def test_duplicate_actions_from_overlapping_chunks_merge():
    a = action(
        "Send the updated pricing page",
        10,
        "I'll send the updated pricing page.",
        owner="Priya",
        uid=1,
    )
    b = action(
        "Send updated pricing page",
        11,
        "I'll send the updated pricing page tomorrow.",
        owner="Priya",
        uid=2,
    )

    result = dedupe([a, b], same_commitment)

    assert len(result) == 1
    assert len(result[0].evidence) == 2
    assert {e.turn_idx for e in result[0].evidence} == {10, 11}


def test_competing_owners_become_ambiguous():
    a = action(
        "Send the updated pricing page",
        10,
        "I'll take it.",
        owner="Alice",
        uid=1,
    )
    b = action(
        "Send the updated pricing page",
        12,
        "I'll take it.",
        owner="Bob",
        uid=2,
    )

    result = merge_competing([a, b])

    assert len(result) == 1
    assert result[0].owner is None
    assert Flag.AMBIGUOUS_OWNER in result[0].flags
    assert set(result[0].owner_candidates) == {"Alice", "Bob"}


def test_deadline_revision_supersedes_instead_of_merging():
    old = action(
        "Submit the final report",
        10,
        "I'll submit the final report by Friday.",
        owner="Alice",
        deadline="Friday",
        uid=1,
    )
    new = action(
        "Submit the final report",
        12,
        "Actually, make that Monday.",
        owner="Alice",
        deadline="Monday",
        uid=2,
        supersedes_hint="Submit the final report",
    )

    result = dedupe([old, new], same_commitment)

    # Different deadlines plus a revision cue prevent deduplication.
    assert len(result) == 2

    apply_supersession(result)

    old_result, new_result = result

    assert old_result.status == "superseded"
    assert old_result.superseded_by_uid == new_result.uid
    assert new_result.status == "committed"


def test_similarly_named_tasks_with_different_owners_do_not_merge():
    a = action(
        "Review the updated pricing page",
        10,
        "Alice will review the updated pricing page.",
        owner_raw="Alice",
        owner="Alice",
        uid=1,
    )
    b = action(
        "Review updated pricing page",
        11,
        "Bob will review the updated pricing page.",
        owner_raw="Bob",
        owner="Bob",
        uid=2,
    )

    assert not same_commitment(a, b)

    result = dedupe([a, b], same_commitment)

    assert len(result) == 2
    assert {item.owner for item in result} == {"Alice", "Bob"}
