import re
from typing import Literal

from pydantic import BaseModel
from rapidfuzz import fuzz

from copilot.extract.chunking import render_turn
from copilot.extract.prompts import load_prompt, render
from copilot.extract.raw_models import ActionCand, RawEvidence
from copilot.extract.structured import generate_validated
from copilot.llm.base import LLMError
from copilot.models import Evidence, Flag, Meeting
from copilot.resolve.owners import FIRST_PERSON, resolve_owner
from copilot.validate.grounding import ground_one, norm

RETRACT = re.compile(
    r"\b(actually|scratch that|never ?mind|instead|make that|change (that|it)|"
    r"on second thought|no wait|forget (that|it)|let's make it|correction)\b",
    re.I,
)

SOCIAL = re.compile(
    r"(can you (all )?(hear|see) (me|us|my screen)|is (this|my) (mic|audio)|"
    r"you there|does that make sense|sound(s)? good|how('s| is) everyone|"
    r"any (other )?questions)",
    re.I,
)

CONF_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def first_turn(c) -> int:
    return min(e.turn_idx for e in c.evidence)


def last_turn(c) -> int:
    return max(e.turn_idx for e in c.evidence)


def _near(a, b, gap: int = 1) -> bool:
    return any(abs(x.turn_idx - y.turn_idx) <= gap for x in a.evidence for y in b.evidence)


def _cue(c) -> bool:
    return any(RETRACT.search(e.quote) for e in c.evidence)


def _first_person(c) -> bool:
    return (c.owner_raw or "").strip().lower() in FIRST_PERSON


# ---------- action items (deterministic) ----------


def preresolve_owners(cands, meeting: Meeting):
    for c in cands:
        r = resolve_owner(
            c.owner_raw,
            c.owner_turn_idx,
            [e.turn_idx for e in c.evidence],
            meeting.turns,
            meeting.roster,
            meeting.aliases,
        )

        c.owner = r.owner
        c.owner_candidates = r.candidates
        c.flags = sorted(
            set(c.flags) | set(r.flags),
            key=lambda f: f.value,
        )


def merge_pair(a, b):
    keep, other = (
        (a, b)
        if (
            CONF_RANK[a.confidence],
            len(a.evidence),
        )
        >= (
            CONF_RANK[b.confidence],
            len(b.evidence),
        )
        else (b, a)
    )

    seen = {(e.turn_idx, norm(e.quote)) for e in keep.evidence}

    keep.evidence += [e for e in other.evidence if (e.turn_idx, norm(e.quote)) not in seen]

    keep.evidence.sort(key=lambda e: e.turn_idx)
    keep.deadline_raw = keep.deadline_raw or other.deadline_raw
    keep.condition = keep.condition or other.condition
    keep.owner = keep.owner or other.owner

    keep.flags = sorted(
        set(keep.flags) | set(other.flags),
        key=lambda f: f.value,
    )

    return keep


def same_commitment(a: ActionCand, b: ActionCand) -> bool:
    if a.status != b.status or not _near(a, b):
        return False

    if (
        fuzz.token_set_ratio(
            norm(a.title),
            norm(b.title),
        )
        < 80
    ):
        return False

    if a.owner and b.owner and a.owner != b.owner:
        return False  # Different people: not a duplicate.

    if (_cue(a) or _cue(b)) and norm(a.deadline_raw or "") != norm(b.deadline_raw or ""):
        return False  # A revision, not a duplicate.

    return True


def dedupe(cands, same):
    out: list = []

    for c in sorted(cands, key=first_turn):
        for i, o in enumerate(out):
            if same(o, c):
                out[i] = merge_pair(o, c)
                break
        else:
            out.append(c)

    return out


def apply_supersession(items: list[ActionCand]) -> None:
    items.sort(key=first_turn)

    for j, later in enumerate(items):
        if later.status == "superseded":
            continue

        hint = later.supersedes_hint

        if not (hint or _cue(later)):
            continue

        target = hint or later.title
        best, best_s = None, 0.0

        for earlier in items[:j] + items[j + 1 :]:
            if earlier is later or earlier.superseded_by_uid is not None:
                continue

            if first_turn(earlier) > first_turn(later):
                continue

            if first_turn(later) - last_turn(earlier) > 20:
                continue

            if set(e.turn_idx for e in earlier.evidence) == set(e.turn_idx for e in later.evidence):
                continue

            s = fuzz.token_set_ratio(
                norm(earlier.title),
                norm(target),
            )

            threshold = 70 if hint else 85

            if s >= threshold and s > best_s:
                best, best_s = earlier, s

        if best:
            best.status = "superseded"
            best.superseded_by_uid = later.uid


def merge_competing(
    items: list[ActionCand],
) -> list[ActionCand]:
    """Two people each say 'I'll take it' for the same task -> one item,
    owner unknown.
    """
    out, used = [], set()

    for i, a in enumerate(items):
        if i in used:
            continue

        if a.status == "committed" and a.owner and _first_person(a):
            group = [a]

            for j in range(i + 1, len(items)):
                b = items[j]

                if (
                    j not in used
                    and b.status == "committed"
                    and b.owner
                    and b.owner != a.owner
                    and _first_person(b)
                    and abs(first_turn(b) - first_turn(a)) <= 4
                    and fuzz.token_set_ratio(
                        norm(a.title),
                        norm(b.title),
                    )
                    >= 80
                    and not _cue(b)
                ):
                    group.append(b)
                    used.add(j)

            if len(group) > 1:
                for g in group[1:]:
                    a = merge_pair(a, g)

                a.owner_candidates = sorted({g.owner for g in group})
                a.owner = None

                a.flags = sorted(
                    set(a.flags) | {Flag.AMBIGUOUS_OWNER},
                    key=lambda f: f.value,
                )

        out.append(a)

    return out


# ---------- questions (LLM judge, grounded) ----------


class Judgement(BaseModel):
    id: str
    status: Literal["answered", "deferred", "unanswered"]
    answer_turn_idx: int | None = None
    answer_quote: str | None = None
    summary: str | None = None


class QuestionJudgements(BaseModel):
    judgements: list[Judgement] = []


def judge_questions(
    router,
    meeting: Meeting,
    qs,
    *,
    window: int = 12,
    batch: int = 4,
):
    prompt = load_prompt("judge_questions_v1")

    results: dict[int, dict] = {}
    degraded = False

    for b in range(0, len(qs), batch):
        group = qs[b : b + batch]
        blocks, ranges = [], []

        for k, q in enumerate(group):
            lo = last_turn(q) + 1
            hi = min(lo + window, len(meeting.turns))

            ranges.append((lo, hi))

            body = "\n".join(render_turn(t) for t in meeting.turns[lo:hi]) or "(end of meeting)"

            blocks.append(
                f"### q{b + k + 1}\n"
                f"Asked at turn {first_turn(q)}: {q.question}\n"
                f"Following turns:\n{body}"
            )

        msgs = render(
            prompt,
            MEETING_DATE=meeting.date.isoformat(),
            QUESTIONS="\n\n".join(blocks),
        )

        try:
            parsed, _ = generate_validated(
                router,
                msgs,
                QuestionJudgements,
                purpose="judge_q",
            )
        except LLMError:
            degraded = True
            parsed = QuestionJudgements()

        by_id = {j.id: j for j in parsed.judgements}

        for k, _q in enumerate(group):
            j = by_id.get(f"q{b + k + 1}")
            lo, hi = ranges[k]

            res = {
                "status": "unanswered",
                "summary": None,
                "evidence": None,
            }

            if j and j.status != "unanswered" and j.answer_quote and j.answer_turn_idx is not None:
                g = ground_one(
                    RawEvidence(
                        turn_idx=j.answer_turn_idx,
                        quote=j.answer_quote,
                    ),
                    meeting.turns,
                )

                if g and lo <= g.turn_idx < hi:
                    res = {
                        "status": j.status,
                        "summary": j.summary,
                        "evidence": Evidence(
                            turn_idx=g.turn_idx,
                            quote=j.answer_quote[:300],
                        ),
                    }

            results[b + k] = res

    return results, degraded


# ---------- decisions (LLM judge, grounded) ----------


class DJudgement(BaseModel):
    id: str
    status: Literal[
        "active",
        "superseded",
        "reversed",
    ] = "active"
    superseded_by: str | None = None
    quote_turn_idx: int | None = None
    quote: str | None = None


class DecisionJudgements(BaseModel):
    decisions: list[DJudgement] = []


def judge_decisions(
    router,
    meeting: Meeting,
    ds,
    *,
    tail: int = 25,
    max_turns: int = 120,
):
    if not ds:
        return {}, False

    prompt = load_prompt("judge_decisions_v1")

    lo = min(first_turn(d) for d in ds)

    hi = min(
        max(last_turn(d) for d in ds) + tail,
        len(meeting.turns),
        lo + max_turns,
    )

    listing = "\n".join(
        f"d{i + 1}: {d.summary} (turns {first_turn(d)}-{last_turn(d)})" for i, d in enumerate(ds)
    )

    excerpt = "\n".join(render_turn(t) for t in meeting.turns[lo:hi])

    msgs = render(
        prompt,
        DECISIONS=listing,
        TRANSCRIPT=excerpt,
    )

    try:
        parsed, _ = generate_validated(
            router,
            msgs,
            DecisionJudgements,
            purpose="judge_d",
        )
    except LLMError:
        return {}, True

    out: dict[int, dict] = {}

    for j in parsed.decisions:
        m = re.fullmatch(r"d(\d+)", j.id)

        if not m or not 1 <= int(m[1]) <= len(ds) or j.status == "active":
            continue

        i = int(m[1]) - 1

        g = (
            ground_one(
                RawEvidence(
                    turn_idx=j.quote_turn_idx or 0,
                    quote=j.quote or "...",
                ),
                meeting.turns,
            )
            if j.quote and j.quote_turn_idx is not None
            else None
        )

        if g and g.turn_idx > last_turn(ds[i]):
            by = re.fullmatch(
                r"d(\d+)",
                j.superseded_by or "",
            )

            out[i] = {
                "status": j.status,
                "by": (int(by[1]) - 1 if by and 1 <= int(by[1]) <= len(ds) else None),
                "evidence": Evidence(
                    turn_idx=g.turn_idx,
                    quote=j.quote[:300],
                ),
            }

    return out, False
