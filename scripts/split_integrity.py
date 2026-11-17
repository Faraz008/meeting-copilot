import hashlib
import json
import sys
from pathlib import Path

from copilot.eval.gold import GoldMeeting

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "data" / "gold" / "test"
MANIFEST = ROOT / "data" / "SPLITS.sha256.json"


def sha(path: Path) -> str:
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def tracked() -> dict[str, str]:
    out = {}

    for gold_path in sorted(TEST_DIR.glob("*.json")):
        out[gold_path.relative_to(ROOT).as_posix()] = sha(gold_path)

        gold = GoldMeeting.model_validate_json(gold_path.read_text(encoding="utf-8"))

        if gold.transcript:
            transcript_path = Path(gold.transcript)
            if not transcript_path.is_absolute():
                transcript_path = ROOT / transcript_path
        else:
            transcript_path = ROOT / "data" / gold.source / f"{gold.meeting_id}.json"

        if transcript_path.exists():
            out[transcript_path.relative_to(ROOT).as_posix()] = sha(transcript_path)

    return out


if __name__ == "__main__":
    cur = tracked()

    if "--write" in sys.argv:
        MANIFEST.write_text(
            json.dumps(cur, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {len(cur)} hashes")
        sys.exit(0)

    if not MANIFEST.exists():
        print("Integrity manifest missing. Run with --write first.")
        sys.exit(1)

    frozen = json.loads(MANIFEST.read_text(encoding="utf-8"))

    bad = [f"{key} (modified or missing)" for key, value in frozen.items() if cur.get(key) != value]

    bad += [f"{key} (new, unfrozen)" for key in cur if key not in frozen]

    if bad:
        print("TEST SPLIT CHANGED since freeze:\n  " + "\n  ".join(bad))
        sys.exit(1)

    print(f"test split matches the freeze ({len(cur)} hashes)")
