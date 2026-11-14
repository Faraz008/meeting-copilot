from pathlib import Path

import pytest

from copilot.parsers.transcript import (
    build_roster,
    has_generic_speakers,
    parse_transcript,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("utf-8")


def test_clean_vtt():
    turns = parse_transcript(load_fixture("clean_vtt.vtt"))

    assert len(turns) == 2
    assert turns[0].speaker == "Priya"
    assert turns[0].text == "Good morning, everyone."
    assert turns[0].start == 1.0
    assert turns[0].end == 3.0
    assert turns[1].speaker == "Rahul"


def test_zoom_vtt():
    turns = parse_transcript(load_fixture("zoom_vtt.vtt"))

    assert len(turns) == 2
    assert turns[0].speaker == "Priya"
    assert turns[0].text == "We should start the meeting."
    assert turns[1].speaker == "Rahul"


def test_srt_comma_timestamps():
    turns = parse_transcript(load_fixture("srt_comma.srt"))

    assert len(turns) == 2
    assert turns[0].start == 1.2
    assert turns[0].end == 3.5
    assert turns[1].start == 4.0
    assert turns[1].end == 6.25


def test_vtt_without_hours():
    turns = parse_transcript(load_fixture("vtt_no_hours.vtt"))

    assert len(turns) == 2
    assert turns[0].start == 65.0
    assert turns[0].end == 68.5
    assert turns[1].start == 69.0
    assert turns[1].end == 72.0


def test_plain_transcript():
    turns = parse_transcript(load_fixture("plain.txt"))

    assert len(turns) == 3
    assert turns[0].speaker == "Priya"
    assert turns[0].text == "Hello everyone."
    assert turns[2].speaker == "Amit"


def test_plain_transcript_with_timestamps():
    turns = parse_transcript(load_fixture("plain_timestamps.txt"))

    assert len(turns) == 3
    assert turns[0].start == 83.0
    assert turns[1].start == 88.0
    assert turns[2].start == 95.0


def test_multiline_continuations():
    turns = parse_transcript(load_fixture("multiline.txt"))

    assert len(turns) == 2
    assert turns[0].speaker == "Priya"
    assert (
        turns[0].text == "We need to complete the backend integration "
        "before Friday. The API endpoints are almost ready."
    )
    assert turns[1].text == "I will take care of the testing and prepare the deployment checklist."


def test_generic_speaker_labels():
    turns = parse_transcript(load_fixture("generic_speakers.txt"))

    roster = build_roster(turns)

    assert roster == ["Speaker 1", "Speaker 2"]
    assert has_generic_speakers(roster)


def test_split_cues_are_merged():
    turns = parse_transcript(load_fixture("split_cue.vtt"))

    assert len(turns) == 2
    assert turns[0].speaker == "Priya"
    assert turns[0].text == "We need to complete the project by Friday."
    assert turns[0].start == 1.0
    assert turns[0].end == 4.0
    assert turns[1].speaker == "Rahul"


@pytest.mark.parametrize(
    "fixture",
    [
        "empty.txt",
        "whitespace.txt",
        "garbage.txt",
    ],
)
def test_empty_or_unrecoverable_transcripts_raise_value_error(fixture):
    with pytest.raises(ValueError):
        parse_transcript(load_fixture(fixture))


def test_bom_and_windows_line_endings():
    turns = parse_transcript(load_fixture("bom_windows.vtt"))

    assert len(turns) == 2
    assert turns[0].speaker == "Priya"
    assert turns[0].text == "Hello from Windows."
    assert turns[1].speaker == "Rahul"


def test_asr_noise_is_preserved():
    turns = parse_transcript(load_fixture("asr_noise.txt"))

    assert len(turns) == 2

    assert "Pree-ya" in turns[0].text
    assert "I I think" in turns[0].text

    assert "yes, yes" in turns[1].text
    assert "um," in turns[1].text
    assert "i am not completely sure" in turns[1].text


def test_text_normalization():
    raw = "<v Priya>  “Um, hello   everyone.”  </v>"

    turns = parse_transcript(f"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n{raw}\n")

    assert turns[0].text == '"Um, hello everyone."'


def test_turn_indices_are_sequential():
    turns = parse_transcript(load_fixture("clean_vtt.vtt"))

    assert [t.idx for t in turns] == list(range(len(turns)))
