import json

from copilot.eval.pred import from_extraction
from copilot.eval.score import (
    ScoreConfig,
    aggregate,
    metrics,
    score_meeting,
)
from copilot.extract.pipeline import run_pipeline
from copilot.io import load_meeting
from copilot.llm.router import Router
from tests.fakes import FakeProvider
from tests.test_pipeline import ev

EVAL_EXTRACT = json.dumps(
    {
        "action_items": [
            {
                "title": "Prepare and send the revised pricing page copy",
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
            }
        ],
        "decisions": [],
        "open_questions": [],
        "follow_ups": [],
    }
)

EVAL_JUDGE_Q = json.dumps({"judgements": []})
EVAL_JUDGE_D = json.dumps({"decisions": []})


def test_scripted_pipeline_scores_perfectly_on_s01():
    meeting, gold = load_meeting("data/gold/dev/s01.json")

    router = Router(
        [
            FakeProvider(
                "fake",
                [EVAL_EXTRACT, EVAL_JUDGE_Q, EVAL_JUDGE_D],
            )
        ],
        sleep=lambda s: None,
    )

    out = run_pipeline(meeting, router)
    pred = from_extraction("s01", "scripted", out.result, out.report)

    assert all(action.status != "superseded" for action in pred.actions)

    result = score_meeting(
        gold,
        pred,
        meeting.turns,
        ScoreConfig(),
    )

    counts = aggregate([result])
    m = metrics(counts)

    # The one gold action must be correctly extracted and matched.
    assert m["act_f1"] == 1.0
    assert m["act_full_recall"] == 1.0

    # Owner, deadline, and status must be correct.
    assert m["act_owner_acc"] == 1.0
    assert m["act_dl_acc"] == 1.0
    assert m["act_status_acc"] == 1.0

    # No decisions, open questions, or follow-ups exist in s01.
    assert m["dec_f1"] is None
    assert m["q_f1"] is None
    assert m["fu_f1"] is None

    # No unresolved questions exist in the gold annotations.
    assert m["q_unres_recall"] is None
    assert m["q_unres_precision"] is None

    # Evidence must be grounded.
    assert m["ungrounded_rate"] == 0.0
