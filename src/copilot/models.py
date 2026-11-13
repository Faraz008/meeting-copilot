from pydantic import BaseModel, Field


class Turn(BaseModel):
    idx: int
    speaker: str | None = None
    start: float | None = None  # seconds
    end: float | None = None
    text: str = Field(min_length=1)
