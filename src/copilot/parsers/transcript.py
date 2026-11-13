import re

from copilot.models import Turn

CUE_TIME = re.compile(r"(?P<s>\d[\d:.,]*)\s*-->\s*(?P<e>\d[\d:.,]*)")
VOICE_TAG = re.compile(r"<v(?:\.[\w.]+)?\s+([^>]+)>")
ANY_TAG = re.compile(r"<[^>]+>")
SPEAKER_PREFIX = re.compile(r"^([A-Z][\w.'\-]*(?: [\w.'\-]+){0,3}):\s+(.*)$")
PLAIN_TS = re.compile(r"^[\[(]?(\d{1,2}:\d{2}(?::\d{2})?)[\])]?\s*[-–]?\s*(.*)$")
GENERIC = re.compile(r"^(speaker|spk|guest|unknown)[\s_-]*\d*$", re.I)


def to_seconds(ts: str) -> float:
    parts = [float(p) for p in ts.replace(",", ".").split(":")]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def clean(text: str) -> str:
    text = ANY_TAG.sub("", text)
    text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", text).strip()


def parse_cues(raw: str) -> list[Turn]:
    raw = raw.replace("\r\n", "\n").lstrip("\ufeff")
    turns: list[Turn] = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        t_i = next((i for i, ln in enumerate(lines) if CUE_TIME.search(ln)), None)
        if t_i is None:
            continue  # WEBVTT header, NOTE blocks, junk
        m = CUE_TIME.search(lines[t_i])
        body = " ".join(lines[t_i + 1 :])
        speaker = None
        v = VOICE_TAG.search(body)
        if v:  # Teams style: <v Name>text</v>
            speaker = v.group(1).strip()
        text = clean(body)
        if not speaker:
            sp = SPEAKER_PREFIX.match(text)  # Zoom style: "Name: text"
            if sp:
                speaker, text = sp.group(1), sp.group(2)
        if text:
            turns.append(
                Turn(
                    idx=0,
                    speaker=speaker,
                    start=to_seconds(m["s"]),
                    end=to_seconds(m["e"]),
                    text=text,
                )
            )
    return merge_adjacent(turns)


def merge_adjacent(turns: list[Turn], max_gap: float = 2.0) -> list[Turn]:
    """Cues often split one sentence; merge same-speaker cues that are close together."""
    out: list[Turn] = []
    for t in turns:
        p = out[-1] if out else None
        if (
            p
            and p.speaker == t.speaker
            and p.end is not None
            and t.start is not None
            and t.start - p.end <= max_gap
        ):
            p.text = f"{p.text} {t.text}"
            p.end = t.end
        else:
            out.append(t.model_copy())
    for i, t in enumerate(out):
        t.idx = i
    return out


def parse_plain(raw: str) -> list[Turn]:
    turns: list[Turn] = []
    for line in raw.replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue
        start = None
        ts = PLAIN_TS.match(line)
        if ts:
            start, line = to_seconds(ts.group(1)), ts.group(2)
        sp = SPEAKER_PREFIX.match(line)
        if sp:
            turns.append(
                Turn(
                    idx=len(turns), speaker=sp.group(1), start=start, text=clean(sp.group(2)) or "…"
                )
            )
        elif turns:  # continuation of previous turn
            turns[-1].text = f"{turns[-1].text} {clean(line)}"
        else:
            turns.append(Turn(idx=0, speaker=None, start=start, text=clean(line)))
    return [t for t in turns if t.text]


def parse_transcript(raw: str) -> list[Turn]:
    turns = parse_cues(raw) if "-->" in raw else parse_plain(raw)
    if not turns:
        raise ValueError("No speech turns found: empty or unrecognized transcript format")
    return turns


def build_roster(turns: list[Turn]) -> list[str]:
    seen: list[str] = []
    for t in turns:
        if t.speaker and t.speaker not in seen:
            seen.append(t.speaker)
    return seen


def has_generic_speakers(roster: list[str]) -> bool:
    return any(GENERIC.match(s) for s in roster)
