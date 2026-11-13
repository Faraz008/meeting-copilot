import json
from pathlib import Path

from copilot.eval.gold import GoldMeeting
from copilot.models import Meeting, Turn

ROOT = Path(__file__).resolve().parents[2]


def resolve_transcript_path(gold: GoldMeeting) -> Path:
    if gold.transcript:
        path = Path(gold.transcript)
        return path if path.is_absolute() else ROOT / path

    return ROOT / "data" / gold.source / f"{gold.meeting_id}.json"


def load_meeting(gold_path: str | Path) -> tuple[Meeting, GoldMeeting]:
    path = Path(gold_path)
    path = path if path.is_absolute() else ROOT / path

    gold = GoldMeeting.model_validate_json(path.read_text(encoding="utf-8"))

    transcript_path = resolve_transcript_path(gold)

    transcript_data = json.loads(transcript_path.read_text(encoding="utf-8"))

    if transcript_data["meeting_id"] != gold.meeting_id:
        raise ValueError(
            f"Transcript meeting_id '{transcript_data['meeting_id']}' "
            f"does not match gold meeting_id '{gold.meeting_id}'"
        )

    turns = [Turn.model_validate(turn_data) for turn_data in transcript_data["turns"]]

    roster = gold.roster or transcript_data.get("roster", [])

    meeting = Meeting(
        meeting_id=gold.meeting_id,
        date=gold.meeting_date,
        timezone=gold.timezone,
        roster=roster,
        aliases=gold.aliases,
        turns=turns,
    )

    return meeting, gold
