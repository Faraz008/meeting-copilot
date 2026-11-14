import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from copilot.extract.chunking import Chunk
from copilot.extract.raw_models import (
    ActionCand,
    DecisionCand,
    FollowUpCand,
    QuestionCand,
    RawAction,
    RawDecision,
    RawEvidence,
    RawFollowUp,
    RawQuestion,
)
from copilot.models import Flag, Turn

_PUNCT = re.compile(r"[^\w\s']")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", _PUNCT.sub(" ", s.lower().replace("\u2019", "'"))).strip()


def quote_score(quote: str, text: str) -> float:
    q, t = norm(quote), norm(text)
    if not q or not t:
        return 0.0
    if len(q) < 12:  # short quotes: whole-word match only ("ok" must not match "book")
        return 100.0 if re.search(rf"\b{re.escape(q)}\b", t) else 0.0
    if q in t:
        return 100.0
    return float(fuzz.partial_ratio(q, t))


@dataclass
class Grounded:
    turn_idx: int
    quote: str
    score: float
    moved: bool


def ground_one(ev: RawEvidence, turns: list[Turn], threshold: float = 85) -> Grounded | None:
    """Exact turn first; then +-1 (models are often off by one). Nothing else is accepted."""
    for k, idx in enumerate((ev.turn_idx, ev.turn_idx - 1, ev.turn_idx + 1)):
        if 0 <= idx < len(turns):
            s = quote_score(ev.quote, turns[idx].text)
            if s >= threshold:
                return Grounded(idx, ev.quote, s, moved=k > 0)
    return None


def phrase_near(
    phrase: str,
    evidence: list[RawEvidence],
    turns: list[Turn],
    radius: int = 2,
    threshold: float = 80,
) -> bool:
    idxs = {
        i
        for e in evidence
        for i in range(e.turn_idx - radius, e.turn_idx + radius + 1)
        if 0 <= i < len(turns)
    }
    return any(quote_score(phrase, turns[i].text) >= threshold for i in idxs)


def _ground_list(evidence, turns, ground: bool):
    if not ground:
        return list(evidence), 0
    good, dropped = [], 0
    for ev in evidence:
        g = ground_one(ev, turns)
        if g:
            good.append(RawEvidence(turn_idx=g.turn_idx, quote=ev.quote))
        else:
            dropped += 1
    return good, dropped


def _build(cls, raw, good, dropped, chunk, extra_flags=None, notes=None):
    data = raw.model_dump()
    data["evidence"] = [e.model_dump() for e in good]
    flags = ([Flag.UNGROUNDED_EVIDENCE] if dropped else []) + (extra_flags or [])
    return cls(**data, flags=flags, chunk_index=chunk.index, notes=notes or [])


def check_action(raw: RawAction, turns, chunk: Chunk, ground: bool = True):
    good, dropped = _ground_list(raw.evidence, turns, ground)
    if not good:
        return None, "ungrounded_evidence"
    if max(e.turn_idx for e in good) < chunk.core_start:
        return None, "context_only"
    c = _build(ActionCand, raw, good, dropped, chunk)
    if not ground:
        return c, None
    if c.deadline_raw and not phrase_near(c.deadline_raw, good, turns):
        c.notes.append(f"deadline_raw_not_in_evidence: {c.deadline_raw!r}")
        c.deadline_raw = None
    if c.condition and not phrase_near(c.condition, good, turns):
        c.notes.append("condition_not_in_evidence")
        c.flags.append(Flag.LOW_CONFIDENCE)
    if c.owner_turn_idx is not None and c.owner_turn_idx not in {e.turn_idx for e in good}:
        c.notes.append("owner_turn_not_in_evidence")
        c.owner_turn_idx = None
    return c, None


def _check_simple(cls, raw, turns, chunk, ground):
    good, dropped = _ground_list(raw.evidence, turns, ground)
    if not good:
        return None, "ungrounded_evidence"
    if max(e.turn_idx for e in good) < chunk.core_start:
        return None, "context_only"
    return _build(cls, raw, good, dropped, chunk), None


def check_decision(raw: RawDecision, turns, chunk, ground=True):
    return _check_simple(DecisionCand, raw, turns, chunk, ground)


def check_question(raw: RawQuestion, turns, chunk, ground=True):
    return _check_simple(QuestionCand, raw, turns, chunk, ground)


def check_followup(raw: RawFollowUp, turns, chunk, ground=True):
    return _check_simple(FollowUpCand, raw, turns, chunk, ground)
