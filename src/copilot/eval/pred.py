from datetime import date

from pydantic import BaseModel

from copilot.eval.gold import GoldMeeting
from copilot.models import ExtractionResult


class PredEvidence(BaseModel):
    turn_idx: int
    quote: str


class _Base(BaseModel):
    turns: list[int] = []  # empty for systems with no evidence (baseline)
    evidence: list[PredEvidence] = []


class PredAction(_Base):
    title: str
    owner: str | None = None
    owner_raw: str | None = None
    deadline: date | None = None
    deadline_options: list[date] = []
    deadline_raw: str | None = None
    status: str = "committed"
    confidence: float = 0.6
    flags: list[str] = []


class PredDecision(_Base):
    summary: str


class PredQuestion(_Base):
    question: str
    answered: bool = False


class PredFollowUp(_Base):
    topic: str


class Prediction(BaseModel):
    meeting_id: str
    system: str
    actions: list[PredAction] = []
    decisions: list[PredDecision] = []
    questions: list[PredQuestion] = []
    follow_ups: list[PredFollowUp] = []
    report: dict = {}
    ok: bool = True
    error: str | None = None


def _ev(items) -> list[PredEvidence]:
    return [PredEvidence(turn_idx=e.turn_idx, quote=e.quote) for e in items]


def _turns(items) -> list[int]:
    return sorted({e.turn_idx for e in items})


def from_extraction(
    meeting_id: str,
    system: str,
    result: ExtractionResult,
    report: dict,
) -> Prediction:
    """Final-state view: superseded actions and non-active
    decisions are dropped (counted in report).
    """
    acts, n_sup = [], 0
    for a in result.action_items:
        if a.status == "superseded":
            n_sup += 1
            continue
        acts.append(
            PredAction(
                title=a.title,
                owner=a.owner,
                owner_raw=a.owner_raw,
                deadline=a.deadline,
                deadline_options=a.deadline_options,
                deadline_raw=a.deadline_raw,
                status=a.status,
                confidence=a.confidence,
                flags=[f.value for f in a.flags],
                turns=_turns(a.evidence),
                evidence=_ev(a.evidence),
            )
        )
    decs = [
        PredDecision(summary=d.summary, turns=_turns(d.evidence), evidence=_ev(d.evidence))
        for d in result.decisions
        if d.status == "active"
    ]
    qs = [
        PredQuestion(
            question=q.question,
            answered=q.answered,
            turns=_turns(q.evidence),
            evidence=_ev(q.evidence),
        )
        for q in result.open_questions
    ]
    fus = [
        PredFollowUp(topic=f.topic, turns=_turns(f.evidence), evidence=_ev(f.evidence))
        for f in result.follow_ups
    ]
    return Prediction(
        meeting_id=meeting_id,
        system=system,
        actions=acts,
        decisions=decs,
        questions=qs,
        follow_ups=fus,
        report={**report, "superseded_actions": n_sup},
    )


def oracle_from_gold(g: GoldMeeting) -> Prediction:
    """Perfect prediction built from the answer key. Used to sanity-check the scorer."""
    return Prediction(
        meeting_id=g.meeting_id,
        system="oracle",
        actions=[
            PredAction(
                title=a.title,
                owner=a.owner,
                deadline=a.deadline,
                status=a.status,
                confidence=1.0,
                turns=a.turns,
            )
            for a in g.action_items
        ],
        decisions=[PredDecision(summary=d.summary, turns=d.turns) for d in g.decisions],
        questions=[
            PredQuestion(question=q.question, answered=q.answered, turns=q.turns)
            for q in g.open_questions
        ],
        follow_ups=[PredFollowUp(topic=f.topic, turns=f.turns) for f in g.follow_ups],
    )
