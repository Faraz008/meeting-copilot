from copilot.resolve.tense import looks_completed


def test_past_action_is_completed():
    assert looks_completed("I sent it yesterday") is True


def test_present_perfect_action_is_completed():
    assert looks_completed("I've already fixed that") is True


def test_future_action_is_not_completed():
    assert looks_completed("I'll send the draft") is False


def test_past_action_with_future_commitment_is_not_completed():
    assert looks_completed("I sent it yesterday but I'll resend by Friday") is False


def test_request_is_not_completed():
    assert looks_completed("Can you send it?") is False
