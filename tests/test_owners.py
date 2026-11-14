import pytest

from copilot.models import Flag, Turn
from copilot.resolve.owners import resolve_owner


@pytest.fixture
def turns():
    return [
        Turn(idx=0, speaker="Sam", text="I will handle the report."),
        Turn(idx=1, speaker="Alex", text="I will review the report."),
        Turn(idx=2, speaker="Sam", text="Let's finish this."),
    ]


def resolve(raw, turns, roster=None, owner_turn_idx=None, evidence_turns=None):
    return resolve_owner(
        raw=raw,
        owner_turn_idx=owner_turn_idx,
        evidence_turns=evidence_turns or [],
        turns=turns,
        roster=roster or ["Sam Lee", "Priya Sharma", "Don Quinn"],
    )


def test_first_person_uses_owner_turn_speaker(turns):
    result = resolve("I", turns, owner_turn_idx=0)

    assert result.owner == "Sam"
    assert result.method == "first_person"
    assert Flag.NO_OWNER not in result.flags


def test_first_person_fallback_with_one_evidence_speaker(turns):
    result = resolve("I", turns, evidence_turns=[0, 2])

    assert result.owner == "Sam"
    assert Flag.LOW_CONFIDENCE in result.flags


def test_first_person_with_multiple_evidence_speakers_is_ambiguous(turns):
    result = resolve("I", turns, evidence_turns=[0, 1])

    assert result.owner is None
    assert Flag.AMBIGUOUS_OWNER in result.flags
    assert set(result.candidates) == {"Sam", "Alex"}


@pytest.mark.parametrize(
    "raw",
    ["we", "someone", "the team", None],
)
def test_group_or_missing_owner_returns_no_owner(raw, turns):
    result = resolve(raw, turns)

    assert result.owner is None
    assert Flag.NO_OWNER in result.flags


@pytest.mark.parametrize(
    "raw",
    ["Pree-ya", "Prya", "Priyaa"],
)
def test_phonetic_matches_resolve_with_low_confidence(raw, turns):
    result = resolve(raw, turns)

    assert result.owner == "Priya Sharma"
    assert Flag.LOW_CONFIDENCE in result.flags
    assert result.method == "phonetic"


def test_full_name_matches_nickname(raw=None):
    turns = [Turn(idx=0, speaker="Speaker 1", text="Samantha will handle it.")]

    result = resolve_owner(
        raw="Samantha",
        owner_turn_idx=None,
        evidence_turns=[0],
        turns=turns,
        roster=["Sam Lee", "Alex Morgan"],
    )

    assert result.owner == "Sam Lee"
    assert result.method == "nickname"


def test_common_first_name_with_multiple_matches_is_ambiguous(turns):
    result = resolve(
        "Sam",
        turns,
        roster=["Sam Lee", "Sam Patel"],
    )

    assert result.owner is None
    assert Flag.AMBIGUOUS_OWNER in result.flags
    assert set(result.candidates) == {"Sam Lee", "Sam Patel"}


def test_similar_short_name_does_not_match_wrong_person(turns):
    result = resolve(
        "Dan",
        turns,
        roster=["Don Quinn"],
    )

    assert result.owner is None
    assert Flag.NO_OWNER in result.flags


def test_role_name_is_not_assigned_as_person(turns):
    result = resolve(
        "Legal",
        turns,
        roster=["Sam Lee", "Priya Sharma", "Don Quinn"],
    )

    assert result.owner is None
    assert Flag.NO_OWNER in result.flags
