import html
import re

from rapidfuzz import fuzz

_MD = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$&])")
FLAG_LABEL = {
    "no_owner": "🙋 no owner",
    "ambiguous_owner": "🙋 ambiguous owner",
    "no_deadline": "📅 no deadline",
    "unresolved_deadline": "📅 deadline unclear",
    "ambiguous_deadline": "📅 deadline ambiguous",
    "low_confidence": "❓ low confidence",
    "proposed_not_committed": "💡 only proposed",
    "ungrounded_evidence": "⚠️ some evidence dropped",
    "conditional": "🔗 conditional",
}
ATTENTION = {
    "no_owner",
    "ambiguous_owner",
    "unresolved_deadline",
    "ambiguous_deadline",
    "low_confidence",
}


def md_escape(s: str | None) -> str:
    """Escape untrusted text before displaying it in st.markdown.

    Neutralizes links, images, emphasis, and headings.
    """
    return _MD.sub(r"\\\1", s or "")


def find_span(
    quote: str,
    text: str,
    min_score: float = 80,
) -> tuple[int, int] | None:
    """Find an exact or approximate quote inside text."""
    q = quote.strip().lower()
    t = text.lower()

    if not q or not t:
        return None

    index = t.find(q)

    if index >= 0:
        return index, index + len(q)

    if len(q) <= len(t):
        alignment = fuzz.partial_ratio_alignment(q, t)

        if alignment and alignment.score >= min_score:
            return (
                alignment.dest_start,
                alignment.dest_end,
            )

    return None


def mark(text: str, quotes: list[str]) -> str:
    """Highlight evidence quotes in HTML-safe text."""
    spans = sorted(span for span in (find_span(quote, text) for quote in quotes) if span)

    merged: list[list[int]] = []

    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(
                merged[-1][1],
                end,
            )
        else:
            merged.append([start, end])

    output = []
    position = 0

    for start, end in merged:
        output.extend(
            [
                html.escape(text[position:start]),
                "<mark>",
                html.escape(text[start:end]),
                "</mark>",
            ]
        )

        position = end

    output.append(html.escape(text[position:]))

    return "".join(output)


def evidence_html(
    turns,
    evidence: list[dict],
    context: int = 2,
) -> str:
    """Build HTML displaying evidence with surrounding context."""
    by_turn: dict[int, list[str]] = {}

    for item in evidence:
        by_turn.setdefault(
            item["turn_idx"],
            [],
        ).append(item["quote"])

    show = sorted(
        {
            index
            for evidence_index in by_turn
            for index in range(
                evidence_index - context,
                evidence_index + context + 1,
            )
            if 0 <= index < len(turns)
        }
    )

    rows = []
    previous = None

    for index in show:
        if previous is not None and index != previous + 1:
            rows.append('<div style="opacity:.5">⋯</div>')

        turn = turns[index]

        speaker = html.escape(turn.speaker or "?")

        highlighted = mark(
            turn.text,
            by_turn.get(index, []),
        )

        rows.append(
            '<div style="margin:2px 0">'
            '<span style="opacity:.6">'
            f"[{index}] {speaker}:"
            "</span> "
            f"{highlighted}"
            "</div>"
        )

        previous = index

    return "".join(rows)


def compute_edits(
    orig: dict,
    new: dict,
) -> dict:
    """Compare form values against the original extraction.

    Setting a field back to its original value removes that edit.
    """
    output = {}

    for key, value in new.items():
        if key == "deadline" and value is not None and not isinstance(value, str):
            value = value.isoformat()

        if value != orig.get(key):
            output[key] = value

    return output


def speaker_samples(
    turns,
    n: int = 3,
) -> dict[str, dict]:
    """Collect speaker statistics and representative samples."""
    output: dict[str, dict] = {}

    for turn in turns:
        speaker = turn.speaker or "?"

        data = output.setdefault(
            speaker,
            {
                "turns": 0,
                "words": 0,
                "samples": [],
            },
        )

        data["turns"] += 1
        data["words"] += len(turn.text.split())

        if len(data["samples"]) < n and len(turn.text) > 25:
            data["samples"].append(turn.text[:110])

    return output
