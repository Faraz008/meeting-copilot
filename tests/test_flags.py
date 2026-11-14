from copilot.models import Flag
from copilot.resolve.flags import action_flags


def get_flags(**overrides):
    values = {
        "status": "committed",
        "owner": "Sam Lee",
        "deadline_raw": "Friday",
        "deadline_status": "resolved",
        "condition": False,
        "confidence_label": "high",
        "existing": set(),
    }
    values.update(overrides)
    return set(action_flags(**values))


def test_proposed_action_gets_proposed_flag():
    assert Flag.PROPOSED_NOT_COMMITTED in get_flags(status="proposed")


def test_missing_owner_gets_no_owner_flag():
    assert Flag.NO_OWNER in get_flags(owner=None)


def test_ambiguous_owner_does_not_get_no_owner_flag():
    flags = get_flags(owner=None, existing={Flag.AMBIGUOUS_OWNER})

    assert Flag.AMBIGUOUS_OWNER in flags
    assert Flag.NO_OWNER not in flags


def test_committed_action_without_deadline_gets_no_deadline_flag():
    assert Flag.NO_DEADLINE in get_flags(deadline_raw=None)


def test_proposed_action_without_deadline_does_not_get_no_deadline_flag():
    assert Flag.NO_DEADLINE not in get_flags(
        status="proposed",
        deadline_raw=None,
    )


def test_unresolvable_deadline_gets_flag():
    assert Flag.UNRESOLVED_DEADLINE in get_flags(
        deadline_status="unresolvable",
    )


def test_ambiguous_deadline_gets_flag():
    assert Flag.AMBIGUOUS_DEADLINE in get_flags(
        deadline_status="ambiguous",
    )


def test_conditional_action_gets_flag():
    assert Flag.CONDITIONAL in get_flags(condition=True)


def test_low_confidence_gets_flag():
    assert Flag.LOW_CONFIDENCE in get_flags(confidence_label="low")


def test_existing_flags_are_preserved():
    existing = {Flag.AMBIGUOUS_DEADLINE}

    assert Flag.AMBIGUOUS_DEADLINE in get_flags(existing=existing)


def test_flags_are_sorted_by_value():
    flags = action_flags(
        status="proposed",
        owner=None,
        deadline_raw=None,
        deadline_status="unresolvable",
        condition=True,
        confidence_label="low",
        existing=set(),
    )

    assert flags == sorted(flags, key=lambda flag: flag.value)
