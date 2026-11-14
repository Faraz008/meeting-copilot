from hypothesis import given
from hypothesis import strategies as st

from copilot.extract.raw_models import RawEvidence
from copilot.models import Turn
from copilot.validate.grounding import ground_one, quote_score

T = [
    Turn(idx=0, speaker="A", text="We should book the venue."),
    Turn(idx=1, speaker="B", text="Okay, I'll send the draft by Friday."),
]


def test_exact():
    g = ground_one(
        RawEvidence(
            turn_idx=1,
            quote="I'll send the draft by Friday.",
        ),
        T,
    )
    assert g is not None
    assert g.score == 100
    assert g.turn_idx == 1
    assert not g.moved


def test_off_by_one_is_repaired():
    g = ground_one(RawEvidence(turn_idx=0, quote="I'll send the draft by Friday"), T)
    assert g and g.turn_idx == 1 and g.moved


def test_fabricated_quote_rejected():
    g = ground_one(
        RawEvidence(
            turn_idx=1,
            quote="I will definitely deploy on Monday.",
        ),
        T,
    )
    assert g is None


def test_short_quote_needs_word_boundary():
    assert quote_score("ok", "go book it") == 0
    assert quote_score("ok", "ok then") == 100


def test_small_asr_noise_tolerated():
    assert quote_score("send the draft by friday", "Okay I'll send the draught by Friday") >= 85


words = st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu")), min_size=2, max_size=8)


@given(st.lists(words, min_size=6, max_size=30), st.data())
def test_any_slice_of_a_turn_grounds(ws, data):
    i = data.draw(st.integers(0, len(ws) - 4))
    j = data.draw(st.integers(i + 3, len(ws)))
    turns = [Turn(idx=0, speaker="A", text=" ".join(ws))]
    assert ground_one(RawEvidence(turn_idx=0, quote=" ".join(ws[i:j])), turns)
