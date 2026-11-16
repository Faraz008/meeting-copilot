from copilot.eval.pred import (
    PredAction,
    PredEvidence,
    Prediction,
    oracle_from_gold,
)
from copilot.eval.score import (
    ScoreConfig,
    aggregate,
    bootstrap_ci,
    metrics,
    score_meeting,
)
from copilot.io import load_meeting


def run(pred_fn, cfg=None, gold_edit=None):
    meeting, g = load_meeting("data/gold/dev/s01.json")
    if gold_edit:
        g = gold_edit(g)
    return score_meeting(g, pred_fn(g), meeting.turns, cfg)


def test_oracle_is_perfect_in_both_matchers():
    for cfg in (ScoreConfig(use_turns=True), ScoreConfig(use_turns=False)):
        c = aggregate([run(oracle_from_gold, cfg)])
        m = metrics(c)

        # s01 contains one gold action.
        assert m["act_f1"] == 1.0
        assert m["act_owner_acc"] == 1.0
        assert m["act_dl_acc"] == 1.0
        assert m["act_status_acc"] == 1.0
        assert m["act_full_recall"] == 1.0

        # Empty categories have undefined F1, represented by None.
        for prefix, key in (
            ("dec", "dec_f1"),
            ("q", "q_f1"),
            ("fu", "fu_f1"),
        ):
            denominator = 2 * c[f"{prefix}_tp"] + c[f"{prefix}_fp"] + c[f"{prefix}_fn"]
            assert m[key] == (1.0 if denominator else None), key

        # No unresolved gold questions or predictions in s01.
        assert m["q_unres_recall"] == (1.0 if c["q_unres_gold"] else None)
        assert m["q_unres_precision"] == (1.0 if c["q_unres_pred"] else None)


def test_empty_prediction():
    m = metrics(aggregate([run(lambda g: Prediction(meeting_id="s01", system="x"))]))

    assert m["act_r"] == 0.0
    assert m["act_p"] is None
    assert m["q_unres_recall"] is None


def test_wrong_owner_and_deadline_are_counted_not_dropped():
    def pf(g):
        p = oracle_from_gold(g)
        p.actions[0].owner = "Dan"
        p.actions[0].deadline = None
        return p

    c = aggregate([run(pf)])

    assert c["act_tp"] == 1
    assert c["act_owner_ok"] == 0
    assert c["dl_missing"] == 1
    assert c["act_full_ok"] == 0


def test_duplicate_prediction_is_a_false_positive():
    def pf(g):
        p = oracle_from_gold(g)
        p.actions.append(p.actions[0].model_copy())
        return p

    assert aggregate([run(pf)])["act_fp"] == 1


def test_turn_matcher_rejects_right_title_wrong_place():
    def pf(g):
        p = oracle_from_gold(g)
        p.actions[0].turns = [0]
        return p

    c = aggregate([run(pf, ScoreConfig(use_turns=True))])

    assert c["act_fp"] == 1
    assert c["act_fn"] == 1

    assert aggregate([run(pf, ScoreConfig(use_turns=False))])["act_fp"] == 0


def test_negative_meeting_counts_spurious_actions():
    c = aggregate(
        [
            run(
                lambda g: Prediction(
                    meeting_id="s01",
                    system="x",
                    actions=[
                        PredAction(
                            title="Invented thing",
                            turns=[3],
                        )
                    ],
                ),
                gold_edit=lambda g: g.model_copy(update={"action_items": []}),
            )
        ]
    )

    assert c["neg_meetings"] == 1
    assert c["neg_pred_actions"] == 1


def test_grounding_audit_catches_fabricated_quote():
    def pf(g):
        p = oracle_from_gold(g)
        p.actions[0].evidence = [
            PredEvidence(
                turn_idx=2,
                quote="I will definitely migrate the database",
            )
        ]
        return p

    assert aggregate([run(pf)])["ev_ungrounded"] == 1


def test_min_conf_filters_predictions():
    def pf(g):
        p = oracle_from_gold(g)
        p.actions[0].confidence = 0.2
        return p

    assert aggregate([run(pf, ScoreConfig(min_conf=0.5))])["act_fn"] == 1


def test_bootstrap_is_deterministic_and_collapses_on_identical_meetings():
    s = [run(oracle_from_gold) for _ in range(4)]

    assert bootstrap_ci(s, "act_f1") == (1.0, 1.0)
    assert bootstrap_ci(s, "act_f1") == bootstrap_ci(s, "act_f1")
