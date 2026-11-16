from collections import Counter
from datetime import date

from pydantic import BaseModel, Field

from copilot.eval.pred import PredAction, PredDecision, Prediction, PredQuestion
from copilot.extract.chunking import render_turn
from copilot.extract.prompts import load_prompt, render
from copilot.extract.structured import generate_validated
from copilot.llm.base import LLMError
from copilot.models import Meeting
from copilot.resolve.owners import resolve_owner


class BaseAction(BaseModel):
    title: str = Field(min_length=1)
    owner: str | None = None
    deadline: str | None = None


class BaselineOut(BaseModel):
    action_items: list[BaseAction] = []
    decisions: list[str] = []
    open_questions: list[str] = []


def _iso(s: str | None) -> date | None:
    try:
        return date.fromisoformat((s or "").strip()[:10])
    except ValueError:
        return None


def run_baseline(meeting: Meeting, router, prompt_name: str = "baseline_v1") -> Prediction:
    prompt = load_prompt(prompt_name)
    transcript = "\n".join(render_turn(t) for t in meeting.turns)
    msgs = render(prompt, MEETING_DATE=meeting.date.isoformat(), TRANSCRIPT=transcript)
    try:
        out, attempts = generate_validated(
            router,
            msgs,
            BaselineOut,
            purpose="baseline",
            max_tokens=4096,
        )
    except LLMError as e:  # includes StructuredFailure and OutputTruncated
        return Prediction(
            meeting_id=meeting.meeting_id,
            system="baseline",
            ok=False,
            error=f"{type(e).__name__}: {e}"[:300],
            report={"complete": False, "chunks": 1},
        )
    acts = []
    for a in out.action_items:
        owner = (
            resolve_owner(
                a.owner,
                None,
                [],
                meeting.turns,
                meeting.roster,
                meeting.aliases,
            ).owner
            if (a.owner or "").strip()
            else None
        )
        acts.append(
            PredAction(
                title=a.title,
                owner=owner,
                owner_raw=a.owner,
                deadline=_iso(a.deadline),
                deadline_raw=a.deadline,
            )
        )
    return Prediction(
        meeting_id=meeting.meeting_id,
        system="baseline",
        actions=acts,
        decisions=[PredDecision(summary=s) for s in out.decisions if s.strip()],
        questions=[
            PredQuestion(question=s, answered=False) for s in out.open_questions if s.strip()
        ],
        report={
            "complete": True,
            "chunks": 1,
            "attempt_kinds": dict(Counter(a.kind for a in attempts)),
            "repairs": sum(1 for a in attempts if a.repaired),
        },
    )
