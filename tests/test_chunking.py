from copilot.extract.chunking import chunk_turns
from copilot.models import Turn


def make_turns(n: int, text: str = "This is a sample transcript sentence.") -> list[Turn]:
    return [
        Turn(
            idx=i,
            speaker=f"Speaker {i % 2 + 1}",
            text=text,
        )
        for i in range(n)
    ]


def test_every_turn_appears_in_at_least_one_chunk():
    turns = make_turns(50)

    chunks = chunk_turns(turns, max_chars=500, overlap=4)

    seen = {turn.idx for chunk in chunks for turn in chunk.turns}

    assert seen == set(range(50))


def test_core_start_ranges_tile_transcript_without_gaps_or_overlap():
    turns = make_turns(50)

    chunks = chunk_turns(turns, max_chars=500, overlap=4)

    assert chunks[0].core_start == 0

    for i, chunk in enumerate(chunks):
        if i + 1 < len(chunks):
            assert chunks[i + 1].core_start > chunk.core_start
            assert chunks[i + 1].core_start <= chunks[i + 1].end + 1

    core_ranges = [
        (
            chunk.core_start,
            chunks[i + 1].core_start if i + 1 < len(chunks) else len(turns),
        )
        for i, chunk in enumerate(chunks)
    ]

    assert core_ranges[0][0] == 0
    assert core_ranges[-1][1] == len(turns)

    for i in range(len(core_ranges) - 1):
        assert core_ranges[i][1] == core_ranges[i + 1][0]

    for start, end in core_ranges:
        assert start < end


def test_no_chunk_exceeds_max_chars_except_single_oversized_turn():
    max_chars = 200
    turns = make_turns(20, text="Short sentence.")

    chunks = chunk_turns(turns, max_chars=max_chars, overlap=2)

    for chunk in chunks:
        rendered_length = len(chunk.render())

        if rendered_length > max_chars:
            assert len(chunk.turns) == 1


def test_single_oversized_turn_gets_its_own_chunk():
    turns = make_turns(3, text="Short sentence.")

    turns[1] = Turn(
        idx=1,
        speaker="Speaker 1",
        text="A" * 1000,
    )

    chunks = chunk_turns(turns, max_chars=100, overlap=1)

    oversized_chunks = [
        chunk for chunk in chunks if any(len(turn.text) > 100 for turn in chunk.turns)
    ]

    assert len(oversized_chunks) == 1
    assert len(oversized_chunks[0].turns) == 1
    assert oversized_chunks[0].turns[0].idx == 1


def test_one_turn_transcript_produces_one_chunk():
    turns = make_turns(1)

    chunks = chunk_turns(turns)

    assert len(chunks) == 1
    assert chunks[0].turns == turns
    assert chunks[0].core_start == 0


def test_500_turn_transcript_terminates_with_tiny_max_chars():
    turns = make_turns(500)

    chunks = chunk_turns(turns, max_chars=1, overlap=4)

    assert len(chunks) > 0

    seen = {turn.idx for chunk in chunks for turn in chunk.turns}

    assert seen == set(range(500))

    assert chunks[0].core_start == 0
    assert chunks[-1].end == 499
