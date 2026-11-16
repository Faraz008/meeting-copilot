import re

from copilot.models import Turn
from copilot.parsers.transcript import build_roster, has_generic_speakers

MIN_WORDS = 20
MAX_CHARS = 400_000
WARN_CHARS = 120_000
MAX_TURN_CHARS = 20_000

EN_STOP = {
    "the",
    "a",
    "an",
    "and",
    "to",
    "of",
    "in",
    "is",
    "it",
    "that",
    "i",
    "we",
    "you",
    "for",
    "on",
    "with",
    "this",
    "be",
    "are",
    "so",
    "do",
    "will",
    "can",
    "have",
    "just",
    "but",
    "not",
}


class InputError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _non_latin_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    return sum(ord(ch) > 0x24F for ch in letters) / len(letters) if letters else 0.0


def estimate_calls(turns: list[Turn], max_chars: int = 8000) -> int:
    chars = sum(len(t.text) + 12 for t in turns)
    chunks = max(1, -(-chars // max_chars))
    return chunks + 2 + len(turns) // 150  # extract + judges (rough)


def prepare_turns(turns: list[Turn], rpm: float = 5.0) -> tuple[list[Turn], list[str]]:
    """Validate and lightly sanitize.
    Raises InputError for unusable input; returns warnings otherwise.
    """
    warnings: list[str] = []
    text = " ".join(t.text for t in turns)
    words = re.findall(r"\w+", text)

    if len(words) < MIN_WORDS:
        raise InputError(
            "too_short",
            f"Transcript has only {len(words)} words (minimum {MIN_WORDS}).",
        )

    alpha = sum(ch.isalpha() for ch in text) / max(1, len(text))

    if alpha < 0.5:
        raise InputError(
            "not_speech",
            "Input does not look like spoken text (too few letters).",
        )

    if len(text) > MAX_CHARS:
        raise InputError(
            "too_long",
            f"Transcript has {len(text):,} characters (limit {MAX_CHARS:,}). Split it.",
        )

    out = []

    for t in turns:
        if len(t.text) > MAX_TURN_CHARS:
            warnings.append(
                f"Turn {t.idx} truncated from {len(t.text):,} to {MAX_TURN_CHARS:,} characters."
            )
            t = t.model_copy(update={"text": t.text[:MAX_TURN_CHARS]})

        out.append(t)

    if len(text) > WARN_CHARS:
        n = estimate_calls(out)
        warnings.append(
            f"Long transcript: about {n} LLM calls (~{n / rpm:.0f} min at {rpm:g} requests/min)."
        )

    roster = build_roster(out)

    if not roster:
        warnings.append(
            "No speaker labels found: owners cannot be resolved; "
            "most tasks will be flagged no_owner."
        )
    elif len(roster) == 1:
        warnings.append(
            "Only one speaker detected: check the labels if this was a multi-person meeting."
        )
    elif len(roster) > 25:
        warnings.append(
            f"{len(roster)} distinct speakers detected: the transcript may be mis-parsed."
        )

    if roster and has_generic_speakers(roster):
        warnings.append(
            "Generic speaker labels (Speaker 1, ...): map them to real names for owner resolution."
        )

    if _non_latin_ratio(text) > 0.3:
        warnings.append(
            "Mostly non-Latin script: English-only in v1; "
            "extraction and date resolution are unreliable."
        )
    elif len(words) >= 50:
        stop = sum(w.lower() in EN_STOP for w in words) / len(words)

        if stop < 0.12:
            warnings.append(
                "Text does not look like English (crude check): results may be unreliable."
            )

    return out, warnings
