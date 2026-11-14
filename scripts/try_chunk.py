import sys

from copilot.extract.chunking import chunk_turns
from copilot.extract.prompts import build_extract_messages, load_prompt
from copilot.io import load_meeting
from copilot.llm.factory import build_router

meeting, gold = load_meeting(sys.argv[1])
prompt = load_prompt(sys.argv[2] if len(sys.argv) > 2 else "extract_v1")
router = build_router()
for ch in chunk_turns(meeting.turns):
    comp = router.complete(
        build_extract_messages(prompt, meeting, ch),
        max_tokens=4096,
    )
    print(
        f"--- chunk {ch.index} turns {ch.start}-{ch.end} via {comp.provider} "
        f"({comp.latency_s:.1f}s, cached={comp.cached})\n{comp.text}\n"
    )
