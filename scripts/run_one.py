import json
import sys
import time
from pathlib import Path

from copilot.extract.pipeline import run_pipeline
from copilot.io import load_meeting
from copilot.llm.factory import build_router


def serialize(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


if len(sys.argv) != 2:
    raise SystemExit("Usage: python scripts/run_one.py <transcript.json>")

input_path = Path(sys.argv[1])

if not input_path.exists():
    raise SystemExit(f"Transcript not found: {input_path}")

meeting, gold = load_meeting(str(input_path))

print(f"\n{'=' * 80}")
print(f"MEETING: {meeting.meeting_id}")
print(f"DATE: {meeting.date}")
print(f"TRANSCRIPT: {input_path}")
print(f"{'=' * 80}\n")

out = run_pipeline(meeting, build_router())

print("ACTION ITEMS")
print("-" * 80)

for item in out.result.action_items:
    flags = ", ".join(flag.value for flag in item.flags) or "-"

    print(
        f"{item.status:12} {(item.owner or '-'):10} {str(item.deadline or '-'):12} | {item.title}"
    )
    print(f"  confidence={item.confidence:.2f} priority={item.priority} flags={flags}")

    for evidence in item.evidence:
        print(f"  evidence[{evidence.turn_idx}]: {evidence.quote}")

    if item.superseded_by:
        print(f"  superseded_by={item.superseded_by}")

print("\nDECISIONS")
print("-" * 80)

for decision in out.result.decisions:
    print(f"- {decision.summary} | status={decision.status}")

print("\nOPEN QUESTIONS")
print("-" * 80)

for question in out.result.open_questions:
    print(f"- answered={question.answered} | {question.question}")

print("\nFOLLOW-UPS")
print("-" * 80)

for followup in out.result.follow_ups:
    print(f"- {followup.topic}")

print("\nPIPELINE REPORT")
print("-" * 80)
print(json.dumps(out.report, indent=2, default=str))

print("\nLOADED GOLD / SECOND RETURN VALUE")
print("-" * 80)
print(json.dumps(serialize(gold), indent=2, default=str))

# Save each run separately. Never overwrite an earlier run.
run_dir = Path("data/runs")
run_dir.mkdir(parents=True, exist_ok=True)

timestamp = int(time.time())
output_path = run_dir / f"{meeting.meeting_id}_{timestamp}.json"

payload = {
    "meeting_id": meeting.meeting_id,
    "input_file": str(input_path),
    "result": out.result.model_dump(mode="json"),
    "report": out.report,
    "gold": serialize(gold),
}

output_path.write_text(
    json.dumps(payload, indent=2, default=str),
    encoding="utf-8",
)

print(f"\nSaved run to: {output_path}")
