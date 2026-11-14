import hashlib
from datetime import date, time
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Turn(BaseModel):
    idx: int
    speaker: str | None = None
    start: float | None = None  # seconds
    end: float | None = None
    text: str = Field(min_length=1)


class Flag(StrEnum):
    NO_OWNER = "no_owner"
    AMBIGUOUS_OWNER = "ambiguous_owner"
    NO_DEADLINE = "no_deadline"
    AMBIGUOUS_DEADLINE = "ambiguous_deadline"
    UNRESOLVED_DEADLINE = "unresolved_deadline"
    LOW_CONFIDENCE = "low_confidence"
    PROPOSED_NOT_COMMITTED = "proposed_not_committed"
    UNGROUNDED_EVIDENCE = "ungrounded_evidence"
    CONDITIONAL = "conditional"


class Evidence(BaseModel):
    turn_idx: int = Field(ge=0)
    quote: str = Field(min_length=3, max_length=400)  # verbatim from the transcript


class ActionItem(BaseModel):
    id: str = ""
    title: str = Field(min_length=3, max_length=100)
    owner_raw: str | None = None
    owner: str | None = None
    deadline_raw: str | None = None
    deadline: date | None = None
    deadline_time: time | None = None
    status: Literal["committed", "proposed", "superseded"] = "committed"
    condition: str | None = None  # "if Dan approves"
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence: list[Evidence] = Field(min_length=1)
    flags: list[Flag] = Field(default_factory=list)
    superseded_by: str | None = None
    deadline_options: list[date] = []  # plausible readings when ambiguous
    owner_candidates: list[str] = []  # competing volunteers
    priority: Literal["high", "normal", "low"] = "normal"

    @field_validator("title")
    @classmethod
    def no_blank_title(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank")
        return v.strip()


class Decision(BaseModel):
    id: str = ""
    summary: str = Field(min_length=3, max_length=200)
    rationale: str | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence: list[Evidence] = Field(min_length=1)
    flags: list[Flag] = Field(default_factory=list)
    status: Literal["active", "superseded", "reversed"] = "active"
    superseded_by: str | None = None


class OpenQuestion(BaseModel):
    id: str = ""
    question: str = Field(min_length=3, max_length=300)
    asked_by: str | None = None
    answered: bool = False
    answer_summary: str | None = None
    evidence: list[Evidence] = Field(min_length=1)


class FollowUp(BaseModel):
    id: str = ""
    topic: str = Field(min_length=3, max_length=200)
    evidence: list[Evidence] = Field(min_length=1)


class ExtractionResult(BaseModel):
    action_items: list[ActionItem] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    follow_ups: list[FollowUp] = Field(default_factory=list)


class Meeting(BaseModel):
    meeting_id: str
    title: str | None = None
    date: date
    timezone: str = "Asia/Kolkata"
    roster: list[str] = Field(default_factory=list)
    turns: list[Turn]
    aliases: dict[str, list[str]] = Field(default_factory=dict)


def stable_id(kind: str, meeting_id: str, first_turn_idx: int, n: int = 0) -> str:
    """ID from position in the transcript, NOT from LLM-generated text, so it survives re-runs."""
    h = hashlib.sha1(f"{kind}|{meeting_id}|{first_turn_idx}|{n}".encode()).hexdigest()
    return f"{kind[:3]}_{h[:10]}"
