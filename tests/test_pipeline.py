import json

from copilot.extract.pipeline import PipelineConfig, run_pipeline
from copilot.io import load_meeting
from copilot.llm.router import Router
from tests.fakes import FakeProvider


def ev(i, quote):
    return {"turn_idx": i, "quote": quote}


EXTRACT = json.dumps(
    {
        "action_items": [
            {
                "title": "Send revised pricing copy",
                "owner_raw": "Sam",
                "owner_turn_idx": 14,
                "deadline_raw": "by Friday",
                "status": "committed",
                "confidence": "high",
                "evidence": [
                    ev(
                        14,
                        "Yes, I'll take the revised pricing copy and send it by Friday.",
                    ),
                    ev(
                        26,
                        "Yes, that's clear. I'll send the copy by Friday.",
                    ),
                ],
            },
            {
                "title": "Review feature names",
                "owner_raw": "I",
                "owner_turn_idx": 18,
                "status": "committed",
                "confidence": "high",
                "evidence": [
                    ev(
                        18,
                        "I can check the feature names separately.",
                    ),
                    ev(
                        27,
                        "I'll review the feature names once the copy is in.",
                    ),
                ],
            },
            {
                "title": "Raise legal cancellation wording check",
                "status": "proposed",
                "confidence": "medium",
                "evidence": [
                    ev(
                        22,
                        "Let's leave that as a proposed check until legal responds.",
                    ),
                    ev(
                        31,
                        "That check can be raised with legal after the copy is handed over.",
                    ),
                ],
            },
            {
                "title": "Invented task",
                "owner_raw": "Dan",
                "confidence": "high",
                "evidence": [
                    ev(
                        10,
                        "I will definitely migrate the database on Monday.",
                    )
                ],
            },
        ],
        "decisions": [
            {
                "summary": "Sam is the single owner of the revised pricing copy",
                "confidence": "high",
                "evidence": [
                    ev(
                        16,
                        "Correct. I am handing it to Sam; I won't be preparing that draft.",
                    ),
                    ev(
                        25,
                        "The handoff is the important change: Sam is the single owner of the copy.",
                    ),
                ],
            }
        ],
        "open_questions": [
            {
                "question": "Does cancellation wording need a footnote?",
                "asked_by": "Dan",
                "evidence": [
                    ev(
                        21,
                        "For legal, we still need to ask whether "
                        "cancellation wording needs a footnote.",
                    )
                ],
            }
        ],
        "follow_ups": [],
    }
)


JUDGE_Q = json.dumps(
    {
        "judgements": [
            {
                "id": "q1",
                "status": "unanswered",
                "answer_turn_idx": None,
                "answer_quote": None,
                "summary": None,
            }
        ]
    }
)


JUDGE_D = json.dumps(
    {
        "decisions": [
            {
                "id": "d1",
                "status": "active",
            }
        ]
    }
)


def make_router():
    return Router(
        [FakeProvider("fake", [EXTRACT, JUDGE_Q, JUDGE_D])],
        sleep=lambda s: None,
    )


def test_s01_end_to_end():
    meeting, _ = load_meeting("data/gold/dev/s01.json")

    out = run_pipeline(meeting, make_router())

    items = {item.title: item for item in out.result.action_items}

    # The invented task must be rejected by grounding.
    assert "Invented task" not in items
    assert out.report["rejected"] == {"ungrounded_evidence": 1}

    # Sam owns the revised pricing copy.
    copy = items["Send revised pricing copy"]

    assert copy.owner == "Sam"
    assert str(copy.deadline) == "2025-03-14"

    # Dan owns the separate feature-name review.
    features = items["Review feature names"]

    assert features.owner == "Dan"

    # The legal check is proposed, not committed.
    legal = items["Raise legal cancellation wording check"]

    assert legal.status == "proposed"
    assert {
        "proposed_not_committed",
        "no_owner",
    } <= {flag.value for flag in legal.flags}

    # The legal question remains unanswered.
    questions = {question.question: question for question in out.result.open_questions}

    assert not questions["Does cancellation wording need a footnote?"].answered

    # The ownership handoff is retained as a decision.
    assert len(out.result.decisions) == 1
    assert out.result.decisions[0].status == "active"

    # No extraction or judging stage degraded.
    assert out.report["complete"] is True
    assert out.report["failed_chunks"] == []
    assert out.report["degraded"] == []


def test_ids_stable_across_runs():
    meeting, _ = load_meeting("data/gold/dev/s01.json")

    ids = []

    for _ in range(2):
        out = run_pipeline(meeting, make_router())

        run_ids = sorted(item.id for item in out.result.action_items)

        ids.append(run_ids)

    assert ids[0] == ids[1]


def test_failed_chunk_marks_pipeline_incomplete():
    meeting, _ = load_meeting("data/gold/dev/s01.json")

    # Every provider response is invalid JSON.
    garbage = ["this is not valid JSON"] * 100

    router = Router(
        [FakeProvider("fake", garbage)],
        sleep=lambda s: None,
    )

    out = run_pipeline(
        meeting,
        router,
        PipelineConfig(use_pass2=False),
    )

    assert out.report["complete"] is False
    assert out.report["failed_chunks"]
