import json
import re
from collections import Counter

from copilot.models import ExtractionResult, Turn


def _luhn(digits: str) -> bool:
    s, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        s += d
        alt = not alt
    return s % 10 == 0


PATTERNS = [  # order matters: specific before generic
    ("KEY", re.compile(r"\b(?:gsk_|sk-|AIza|ghp_|xox[bap]-|hf_|ntn_)[A-Za-z0-9_\-]{16,}")),
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("URL", re.compile(r"https?://[^\s<>\"]+")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){12,18}\d\b")),
    (
        "AADHAAR",
        re.compile(r"(?<!\d)(?<!\d[ -])[2-9]\d{3}(?:[ -]?\d{4}){2}(?![ -]?\d)"),
    ),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    (
        "PHONE",
        re.compile(
            r"(?<![\w/])(?:\+\d{1,3}[ .-]?\d(?:[ .-]?\d){7,11}|[6-9]\d{4}[ -]?\d{5}"
            r"|\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4})(?![\w/])"
        ),
    ),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


class Redactor:
    def __init__(self) -> None:
        self._map: dict[str, str] = {}
        self._rev: dict[tuple[str, str], str] = {}
        self._n: Counter = Counter()

    def _token(self, label: str, value: str) -> str:
        key = (label, value)
        if key not in self._rev:
            self._n[label] += 1
            tok = f"[{label}_{self._n[label]}]"
            self._rev[key], self._map[tok] = tok, value
        return self._rev[key]

    def redact_text(self, text: str) -> str:
        for label, pat in PATTERNS:

            def sub(m: re.Match, label=label) -> str:
                v = m.group(0)
                if label == "CARD":
                    digits = re.sub(r"\D", "", v)
                    if not 13 <= len(digits) <= 19 or not _luhn(digits):
                        return v
                return self._token(label, v)

            text = pat.sub(sub, text)
        return text

    def redact_turns(self, turns: list[Turn]) -> list[Turn]:
        return [t.model_copy(update={"text": self.redact_text(t.text)}) for t in turns]

    def restore_text(self, s: str) -> str:
        for tok, val in self._map.items():
            s = s.replace(tok, val)
        return s

    def restore_result(self, r: ExtractionResult) -> ExtractionResult:
        """The pipeline ran on tokenized text (so quotes were grounded against it);
        swap originals back in."""
        data = r.model_dump_json()
        for tok, val in self._map.items():
            data = data.replace(tok, json.dumps(val, ensure_ascii=False)[1:-1])
        return ExtractionResult.model_validate_json(data)

    def counts(self) -> dict[str, int]:
        return dict(self._n)
