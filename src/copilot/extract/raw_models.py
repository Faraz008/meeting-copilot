from typing import Literal

from pydantic import BaseModel, Field, field_validator

from copilot.models import Flag


class RawEvidence(BaseModel):
    turn_idx: int = Field(ge=0)
    quote: str = Field(min_length=3)

    @field_validator("quote")
    @classmethod
    def _trim(cls, v: str) -> str:
        return v.strip()[:300]


class RawAction(BaseModel):
    title: str = Field(min_length=3)
    owner_raw: str | None = None
    owner_turn_idx: int | None = None  # turn where the owner says "I"/accepts
    deadline_raw: str | None = None
    status: Literal["committed", "proposed", "superseded"] = "committed"
    condition: str | None = None
    supersedes_hint: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"
    evidence: list[RawEvidence] = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def _trim(cls, v: str) -> str:
        return v.strip()[:100]


class RawDecision(BaseModel):
    summary: str = Field(min_length=3)
    rationale: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"
    evidence: list[RawEvidence] = Field(min_length=1)

    @field_validator("summary")
    @classmethod
    def _trim(cls, v: str) -> str:
        return v.strip()[:200]


class RawQuestion(BaseModel):
    question: str = Field(min_length=3)
    asked_by: str | None = None
    evidence: list[RawEvidence] = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def _trim(cls, v: str) -> str:
        return v.strip()[:300]


class RawFollowUp(BaseModel):
    topic: str = Field(min_length=3)
    evidence: list[RawEvidence] = Field(min_length=1)

    @field_validator("topic")
    @classmethod
    def _trim(cls, v: str) -> str:
        return v.strip()[:200]


class RawExtraction(BaseModel):
    action_items: list[RawAction] = []
    decisions: list[RawDecision] = []
    open_questions: list[RawQuestion] = []
    follow_ups: list[RawFollowUp] = []


# ---- candidates: raw items after grounding, carrying pipeline state ----
class _Cand(BaseModel):
    flags: list[Flag] = []
    chunk_index: int = 0
    notes: list[str] = []


class ActionCand(_Cand, RawAction):
    uid: int = 0
    owner: str | None = None
    owner_candidates: list[str] = []
    superseded_by_uid: int | None = None


class DecisionCand(_Cand, RawDecision): ...


class QuestionCand(_Cand, RawQuestion): ...


class FollowUpCand(_Cand, RawFollowUp): ...
