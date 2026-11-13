import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from copilot.eval.gold import KNOWN_TAGS, GoldMeeting

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("dev", "test")


def resolve_transcript_path(gold: GoldMeeting) -> Path:
    if gold.transcript:
        path = Path(gold.transcript)
        return path if path.is_absolute() else ROOT / path

    return ROOT / "data" / gold.source / f"{gold.meeting_id}.json"


def check(path: Path):
    errors: list[str] = []
    warnings: list[str] = []

    try:
        gold = GoldMeeting.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        return None, [f"schema error: {exc}"], warnings

    if gold.meeting_id != path.stem:
        errors.append(f"meeting_id '{gold.meeting_id}' != filename '{path.stem}'")

    transcript_path = resolve_transcript_path(gold)

    if not transcript_path.exists():
        message = f"transcript missing: {transcript_path}"

        if gold.source == "synthetic":
            errors.append(message)
        else:
            warnings.append(message)

        return gold, errors, warnings

    try:
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"could not read transcript JSON: {exc}")
        return gold, errors, warnings

    if not isinstance(transcript, dict):
        errors.append("transcript root must be a JSON object")
        return gold, errors, warnings

    transcript_id = transcript.get("meeting_id")

    if transcript_id != gold.meeting_id:
        errors.append(
            f"transcript meeting_id '{transcript_id}' "
            f"does not match gold meeting_id '{gold.meeting_id}'"
        )

    transcript_date = transcript.get("date")

    if transcript_date:
        try:
            parsed_date = date.fromisoformat(transcript_date)
            if parsed_date != gold.meeting_date:
                errors.append(
                    f"transcript date {parsed_date} does not match "
                    f"gold meeting_date {gold.meeting_date}"
                )
        except (TypeError, ValueError):
            errors.append(f"invalid transcript date: {transcript_date}")

    turns = transcript.get("turns")

    if not isinstance(turns, list) or not turns:
        errors.append("transcript must contain a non-empty turns list")
        return gold, errors, warnings

    valid_turn_ids: set[int] = set()
    speakers: set[str] = set()

    for position, turn in enumerate(turns):
        if not isinstance(turn, dict):
            errors.append(f"turn at position {position} must be an object")
            continue

        turn_idx = turn.get("idx")

        if not isinstance(turn_idx, int) or isinstance(turn_idx, bool):
            errors.append(f"turn at position {position} has invalid idx: {turn_idx}")
        elif turn_idx in valid_turn_ids:
            errors.append(f"duplicate transcript turn idx: {turn_idx}")
        else:
            valid_turn_ids.add(turn_idx)

        speaker = turn.get("speaker")

        if isinstance(speaker, str) and speaker.strip():
            speakers.add(speaker)

    for name in set(gold.roster) - speakers:
        warnings.append(f"roster name '{name}' never speaks (may be mentioned only)")

    for speaker in speakers - set(gold.roster):
        warnings.append(f"speaker '{speaker}' is not in gold roster")

    groups = [
        gold.action_items,
        gold.decisions,
        gold.open_questions,
        gold.follow_ups,
    ]

    all_items = [item for group in groups for item in group]
    ids = [item.gold_id for item in all_items]

    for gold_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate gold_id '{gold_id}'")

    for item in all_items:
        invalid_turns = [turn_idx for turn_idx in item.turns if turn_idx not in valid_turn_ids]

        if invalid_turns:
            errors.append(f"{item.gold_id}: invalid turn indexes {invalid_turns}")

        unknown_tags = set(item.tags) - KNOWN_TAGS

        if unknown_tags:
            errors.append(f"{item.gold_id}: unknown tags {sorted(unknown_tags)}")

    for action in gold.action_items:
        if action.owner and action.owner not in gold.roster:
            errors.append(f"{action.gold_id}: owner '{action.owner}' is not in roster")

        if "ambiguous_owner" in action.tags and action.owner:
            errors.append(f"{action.gold_id}: ambiguous_owner items must have owner null")

        if (
            action.status == "committed"
            and not action.owner
            and not {"no_owner", "ambiguous_owner"} & set(action.tags)
        ):
            warnings.append(
                f"{action.gold_id}: committed action has no owner "
                "and is not tagged no_owner/ambiguous_owner"
            )

        if action.deadline and action.deadline < gold.meeting_date:
            warnings.append(f"{action.gold_id}: deadline is before meeting date")

    return gold, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gold-dir",
        type=Path,
        help="Validate one gold directory instead of both splits",
    )
    args = parser.parse_args()

    if args.gold_dir:
        gold_dir = args.gold_dir
        if not gold_dir.is_absolute():
            gold_dir = ROOT / gold_dir

        directories = [(gold_dir.name, gold_dir)]
    else:
        directories = [(split, ROOT / "data" / "gold" / split) for split in SPLITS]

    failed = False
    seen_meetings: dict[str, str] = {}
    coverage = {name: Counter() for name, _ in directories}
    counts = Counter()

    for split, directory in directories:
        files = sorted(directory.glob("*.json"))

        if not files:
            print(f"ERROR {directory}: no gold JSON files found")
            failed = True
            continue

        for path in files:
            gold, errors, warnings = check(path)
            counts[split] += 1

            for warning in warnings:
                print(f"WARN  {split}/{path.name}: {warning}")

            for error in errors:
                print(f"ERROR {split}/{path.name}: {error}")
                failed = True

            if gold is None:
                continue

            previous_split = seen_meetings.get(gold.meeting_id)

            if previous_split:
                print(f"ERROR {gold.meeting_id} appears in both {previous_split} and {split}")
                failed = True
            else:
                seen_meetings[gold.meeting_id] = split

            for item in gold.action_items + gold.decisions + gold.open_questions + gold.follow_ups:
                coverage[split].update(item.tags)

    print(f"\nfiles: {dict(counts)}")

    for split, tags in coverage.items():
        print(f"tag coverage [{split}]: {dict(sorted(tags.items()))}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
