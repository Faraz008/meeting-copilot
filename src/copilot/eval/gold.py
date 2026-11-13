from datetime import date
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field

KNOWN_TAGS = {
    "retraction",
    "revision",
    "proposed",
    "unresolved_q",
    "unanswered",
    "crosstalk",
    "asr_error",
    "relative_date",
    "ambiguous_owner",
    "conditional",
    "no_owner",
    "decision_reversal",
    "recap",
    "nickname",
    "past_tense_negative",
    "single_speaker",
    "event_relative_deadline",
    "no_deadline",
    "deferred",
    "real",
}


class GoldAction(BaseModel):
    gold_id: str
    title: str
    owner: str | None = None
    deadline: date | None = None
    status: Literal["committed", "proposed"] = "committed"
    condition: str | None = None
    turns: list[int] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class GoldDecision(BaseModel):
    gold_id: str
    summary: str = Field(validation_alias=AliasChoices("summary", "title"))
    previous_decision: str | None = None
    turns: list[int] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class GoldQuestion(BaseModel):
    gold_id: str
    question: str = Field(validation_alias=AliasChoices("question", "title"))
    answered: bool
    turns: list[int] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class GoldFollowUp(BaseModel):
    gold_id: str
    topic: str = Field(validation_alias=AliasChoices("topic", "title"))
    deadline: date | None = None
    turns: list[int] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class GoldMeeting(BaseModel):
    meeting_id: str
    source: Literal["synthetic", "real"] = "synthetic"
    transcript: str | None = None

    meeting_date: date
    timezone: str = "Asia/Kolkata"
    roster: list[str] = Field(default_factory=list)
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    notes: str | None = None

    action_items: list[GoldAction] = Field(default_factory=list)
    decisions: list[GoldDecision] = Field(default_factory=list)
    open_questions: list[GoldQuestion] = Field(default_factory=list)
    follow_ups: list[GoldFollowUp] = Field(default_factory=list)
