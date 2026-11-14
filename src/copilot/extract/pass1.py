from dataclasses import asdict, dataclass, field

from copilot.extract.chunking import Chunk, chunk_turns, split_chunk
from copilot.extract.prompts import build_extract_messages, load_prompt
from copilot.extract.raw_models import RawExtraction
from copilot.extract.structured import (
    OutputTruncated,
    StructuredFailure,
    generate_validated,
)
from copilot.llm.base import LLMError
from copilot.models import Meeting
from copilot.validate.grounding import (
    check_action,
    check_decision,
    check_followup,
    check_question,
)


@dataclass
class Pass1Result:
    actions: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    questions: list = field(default_factory=list)
    followups: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    failed_chunks: list = field(default_factory=list)
    attempts: list = field(default_factory=list)

    raw_counts: dict = field(
        default_factory=lambda: {
            "action": 0,
            "decision": 0,
            "question": 0,
            "followup": 0,
        }
    )

    n_chunks: int = 0
    prompt_sha: str = ""


def extract_chunk(
    router,
    prompt,
    meeting: Meeting,
    chunk: Chunk,
    depth: int = 0,
):
    messages = build_extract_messages(prompt, meeting, chunk)

    try:
        raw, attempts = generate_validated(
            router,
            messages,
            RawExtraction,
            purpose="extract",
        )

        return [(raw, chunk, attempts)]

    except OutputTruncated as e:
        if len(chunk.turns) < 6 or depth >= 2:
            raise StructuredFailure([]) from e

        out = []

        for part in split_chunk(chunk):
            out += extract_chunk(
                router,
                prompt,
                meeting,
                part,
                depth + 1,
            )

        return out


def run_pass1(
    router,
    meeting: Meeting,
    *,
    prompt_name: str = "extract_v1",
    max_chars: int = 8000,
    overlap: int = 4,
    ground: bool = True,
) -> Pass1Result:
    prompt = load_prompt(prompt_name)

    res = Pass1Result(prompt_sha=prompt.sha)

    chunks = chunk_turns(
        meeting.turns,
        max_chars,
        overlap,
    )

    res.n_chunks = len(chunks)

    for chunk in chunks:
        try:
            pieces = extract_chunk(
                router,
                prompt,
                meeting,
                chunk,
            )

        except (StructuredFailure, LLMError) as e:
            # Never silently drop a failed chunk.
            res.failed_chunks.append(
                {
                    "chunk": chunk.index,
                    "turns": [
                        chunk.start,
                        chunk.end,
                    ],
                    "error": str(e)[:300],
                }
            )
            continue

        for raw, ch, attempts in pieces:
            res.attempts += [asdict(a) for a in attempts]

            specs = [
                (
                    "action",
                    raw.action_items,
                    check_action,
                    res.actions,
                    "title",
                ),
                (
                    "decision",
                    raw.decisions,
                    check_decision,
                    res.decisions,
                    "summary",
                ),
                (
                    "question",
                    raw.open_questions,
                    check_question,
                    res.questions,
                    "question",
                ),
                (
                    "followup",
                    raw.follow_ups,
                    check_followup,
                    res.followups,
                    "topic",
                ),
            ]

            for kind, items, checker, sink, label in specs:
                for item in items:
                    res.raw_counts[kind] += 1

                    cand, why = checker(
                        item,
                        meeting.turns,
                        ch,
                        ground,
                    )

                    if cand:
                        sink.append(cand)
                    else:
                        res.rejected.append(
                            {
                                "kind": kind,
                                "text": getattr(item, label),
                                "reason": why,
                            }
                        )

    return res
