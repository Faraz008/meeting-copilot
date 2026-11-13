import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

GOLD_DIR = ROOT / "data" / "gold"
TRANSCRIPT_DIRS = [
    ROOT / "data" / "synthetic",
    ROOT / "data" / "raw",
]

ITEM_CATEGORIES = (
    "action_items",
    "decisions",
    "open_questions",
    "follow_ups",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")

    return data


def find_transcript(meeting_id: str) -> Path | None:
    """Find the transcript corresponding to a gold meeting."""
    for directory in TRANSCRIPT_DIRS:
        path = directory / f"{meeting_id}.json"
        if path.is_file():
            return path

    return None


def validate_date(value: Any, field: str, errors: list[str]) -> None:
    """Check that a value is a valid ISO-8601 calendar date."""
    if not isinstance(value, str):
        errors.append(f"{field}: expected a date string")
        return

    try:
        date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field}: invalid date {value!r}")


def get_transcript_turns(
    transcript: dict[str, Any],
    path: Path,
    errors: list[str],
) -> set[int]:
    """Extract valid turn indexes from a transcript JSON file."""
    turns = transcript.get("turns")

    if not isinstance(turns, list):
        errors.append(f"{path}: expected a 'turns' list")
        return set()

    indexes: set[int] = set()

    for position, turn in enumerate(turns):
        if not isinstance(turn, dict):
            errors.append(f"{path}: turns[{position}] must be an object")
            continue

        idx = turn.get("idx")

        if isinstance(idx, bool) or not isinstance(idx, int) or idx < 0:
            errors.append(f"{path}: turns[{position}] has an invalid idx")
            continue

        if idx in indexes:
            errors.append(f"{path}: duplicate transcript turn index {idx}")

        indexes.add(idx)

    return indexes


def validate_gold_file(gold_path: Path) -> list[str]:
    errors: list[str] = []

    try:
        gold = load_json(gold_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"{gold_path}: cannot read gold file: {exc}"]

    meeting_id = gold.get("meeting_id")

    if not isinstance(meeting_id, str) or not meeting_id.strip():
        return [f"{gold_path}: missing or invalid meeting_id"]

    validate_date(gold.get("meeting_date"), "meeting_date", errors)

    roster = gold.get("roster")

    if not isinstance(roster, list) or not all(
        isinstance(name, str) and name.strip() for name in roster
    ):
        errors.append("roster: expected a list of non-empty names")
        roster = []

    transcript_path = find_transcript(meeting_id)

    if transcript_path is None:
        errors.append(f"{meeting_id}: transcript not found in data/synthetic/ or data/raw/")
        return errors

    try:
        transcript = load_json(transcript_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"{transcript_path}: cannot read transcript: {exc}")
        return errors

    valid_turns = get_transcript_turns(
        transcript,
        transcript_path,
        errors,
    )

    seen_ids: set[str] = set()

    for category in ITEM_CATEGORIES:
        items = gold.get(category, [])

        if not isinstance(items, list):
            errors.append(f"{category}: expected a list")
            continue

        for position, item in enumerate(items):
            location = f"{category}[{position}]"

            if not isinstance(item, dict):
                errors.append(f"{location}: expected an object")
                continue

            gold_id = item.get("gold_id")

            if not isinstance(gold_id, str) or not gold_id.strip():
                errors.append(f"{location}: missing or invalid gold_id")
            elif gold_id in seen_ids:
                errors.append(f"{location}: duplicate gold_id {gold_id!r}")
            else:
                seen_ids.add(gold_id)

            turns = item.get("turns")

            if not isinstance(turns, list) or not turns:
                errors.append(f"{location}: turns must be a non-empty list")
            else:
                for turn_idx in turns:
                    if isinstance(turn_idx, bool) or not isinstance(turn_idx, int) or turn_idx < 0:
                        errors.append(f"{location}: invalid turn index {turn_idx!r}")
                    elif turn_idx not in valid_turns:
                        errors.append(
                            f"{location}: turn index {turn_idx} does not exist in transcript"
                        )

            if category == "action_items":
                owner = item.get("owner")

                if owner is not None and owner not in roster:
                    errors.append(f"{location}: owner {owner!r} is not in the meeting roster")

                if "deadline" in item and item["deadline"] is not None:
                    validate_date(
                        item["deadline"],
                        f"{location}.deadline",
                        errors,
                    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate meeting gold files against their transcripts."
    )
    parser.add_argument(
        "--gold-dir",
        type=Path,
        default=GOLD_DIR,
        help="Directory containing gold JSON files.",
    )
    args = parser.parse_args()

    gold_files = sorted(args.gold_dir.glob("*.json"))

    if not gold_files:
        print(f"ERROR: No gold JSON files found in {args.gold_dir}")
        return 1

    total_errors = 0

    for gold_path in gold_files:
        errors = validate_gold_file(gold_path)

        if errors:
            print(f"\nFAIL: {gold_path.relative_to(ROOT)}")
            for error in errors:
                print(f"  - {error}")
            total_errors += len(errors)
        else:
            print(f"PASS: {gold_path.relative_to(ROOT)}")

    if total_errors:
        print(f"\nValidation failed: {total_errors} error(s).")
        return 1

    print(f"\nAll {len(gold_files)} gold file(s) passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
