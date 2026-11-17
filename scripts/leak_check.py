import re
import sys
from pathlib import Path

from copilot.eval.gold import GoldMeeting

ROOT = Path(__file__).resolve().parents[1]
N = 8


def grams(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(words[i : i + N]) for i in range(len(words) - N + 1)}


def resolve_transcript_path(gold: GoldMeeting) -> Path:
    if gold.transcript:
        path = Path(gold.transcript)
        return path if path.is_absolute() else ROOT / path

    return ROOT / "data" / gold.source / f"{gold.meeting_id}.json"


def transcript_text(path: Path) -> str:
    import json

    data = json.loads(path.read_text(encoding="utf-8"))

    turns = data.get("turns", [])
    parts = []

    for turn in turns:
        if isinstance(turn, dict):
            parts.append(str(turn.get("text", "")))

    return "\n".join(parts)


def main() -> int:
    bad = []
    transcripts = {}

    for split in ("dev", "test"):
        gold_dir = ROOT / "data" / "gold" / split

        for gold_path in sorted(gold_dir.glob("*.json")):
            gold = GoldMeeting.model_validate_json(gold_path.read_text(encoding="utf-8"))

            path = resolve_transcript_path(gold)

            if not path.exists():
                print(f"ERROR: missing transcript for {gold.meeting_id}: {path}")
                return 1

            transcripts[f"{split}/{gold.meeting_id}"] = grams(transcript_text(path))

    prompt_dir = ROOT / "prompts"

    for prompt_path in sorted(prompt_dir.glob("*.md")):
        prompt_grams = grams(prompt_path.read_text(encoding="utf-8"))

        for name, transcript_grams in transcripts.items():
            hit = prompt_grams & transcript_grams

            if hit:
                bad.append(
                    f"{prompt_path.name} shares {len(hit)} "
                    f"{N}-grams with {name}, "
                    f"e.g. {sorted(hit)[0]!r}"
                )

    print("\n".join(bad) or "no prompt/transcript overlap")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
