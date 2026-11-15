import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from copilot.eval.gold import GoldMeeting
from copilot.eval.matching import match_items, near
from copilot.eval.pred import Prediction
from copilot.extract.raw_models import RawEvidence
from copilot.models import Turn
from copilot.validate.grounding import ground_one


@dataclass
class ScoreConfig:
    use_turns: bool = True
    min_title: float | None = None
    tol: int = 1
    min_conf: float = 0.0
    exclude_proposed: bool = False


@dataclass
class MeetingScore:
    meeting_id: str
    counts: Counter = field(default_factory=Counter)
    tags: dict = field(default_factory=lambda: defaultdict(Counter))
    details: dict = field(default_factory=lambda: {"fn": [], "fp": [], "bad": []})


def _ungrounded(items, turns: list[Turn]) -> tuple[int, int]:
    n = bad = 0
    for it in items:
        if not it.evidence:
            continue
        n += 1
        ok = False
        for e in it.evidence:
            try:
                ok = (
                    ground_one(
                        RawEvidence(turn_idx=e.turn_idx, quote=e.quote),
                        turns,
                    )
                    is not None
                )
            except ValueError:  # quote too short to even validate
                ok = False
            if ok:
                break
        bad += not ok
    return n, bad


def score_meeting(
    g: GoldMeeting,
    pred: Prediction,
    turns: list[Turn],
    cfg: ScoreConfig | None = None,
) -> MeetingScore:
    cfg = cfg or ScoreConfig()
    ms = MeetingScore(g.meeting_id)
    c, det = ms.counts, ms.details
    c["meetings"] += 1
    if not pred.ok:
        c["sys_failed"] += 1
    if pred.report.get("complete") is False:
        c["incomplete"] += 1
    min_title = cfg.min_title if cfg.min_title is not None else (40.0 if cfg.use_turns else 60.0)

    g_acts = [a for a in g.action_items if not (cfg.exclude_proposed and a.status == "proposed")]
    p_acts = [
        a
        for a in pred.actions
        if a.confidence >= cfg.min_conf and not (cfg.exclude_proposed and a.status == "proposed")
    ]

    def run_kind(kind, pre, G, P, gt, pt):
        pairs = match_items(
            [gt(x) for x in G],
            [x.turns for x in G],
            [pt(x) for x in P],
            [x.turns for x in P],
            use_turns=cfg.use_turns,
            min_title=min_title,
            tol=cfg.tol,
        )
        mg = {x.gold_i for x in pairs}
        mp = {x.pred_i for x in pairs}
        c[f"{pre}_tp"] += len(pairs)
        c[f"{pre}_fp"] += len(P) - len(pairs)
        c[f"{pre}_fn"] += len(G) - len(pairs)

        for gi, gx in enumerate(G):
            for t in gx.tags:
                ms.tags[t]["n"] += 1
                ms.tags[t]["hit"] += gi in mg
            if gi in mg:
                continue
            det["fn"].append(
                {
                    "type": "fn",
                    "kind": kind,
                    "id": gx.gold_id,
                    "text": gt(gx),
                    "turns": gx.turns,
                    "tags": gx.tags,
                    "status": getattr(gx, "status", None),
                    "near_pred": [
                        pt(px)
                        for px in P
                        if cfg.use_turns and px.turns and near(px.turns, gx.turns, cfg.tol)
                    ],
                }
            )

        for pi, px in enumerate(P):
            if pi in mp:
                continue
            det["fp"].append(
                {
                    "type": "fp",
                    "kind": kind,
                    "text": pt(px),
                    "turns": px.turns,
                    "status": getattr(px, "status", None),
                    "owner": getattr(px, "owner", None),
                    "owner_raw": getattr(px, "owner_raw", None),
                    "flags": getattr(px, "flags", []),
                    "conf": getattr(px, "confidence", None),
                    "quotes": " | ".join(e.quote for e in px.evidence),
                    "near_gold": [
                        {
                            "id": gx.gold_id,
                            "text": gt(gx),
                            "matched": gi in mg,
                        }
                        for gi, gx in enumerate(G)
                        if cfg.use_turns and near(px.turns, gx.turns, cfg.tol)
                    ],
                }
            )
        return pairs

    # ---- actions ----
    for x in run_kind(
        "action",
        "act",
        g_acts,
        p_acts,
        lambda a: a.title,
        lambda a: a.title,
    ):
        gx, px = g_acts[x.gold_i], p_acts[x.pred_i]
        c["act_matched"] += 1
        issues = []

        if px.owner == gx.owner:
            c["act_owner_ok"] += 1
        else:
            issues.append("owner")

        if px.deadline == gx.deadline:
            c["act_dl_ok"] += 1
            c["act_dl_lenient_ok"] += 1
        else:
            issues.append("deadline")
            if gx.deadline and gx.deadline in px.deadline_options:
                c["act_dl_lenient_ok"] += 1
            if gx.deadline and not px.deadline:
                c["dl_missing"] += 1
            elif px.deadline and not gx.deadline:
                c["dl_invented"] += 1
            else:
                c["dl_wrong"] += 1

        if px.status == gx.status:
            c["act_status_ok"] += 1
        else:
            issues.append("status")

        if issues:
            det["bad"].append(
                {
                    "type": "bad",
                    "kind": "action",
                    "id": gx.gold_id,
                    "text": gx.title,
                    "pred_text": px.title,
                    "issues": issues,
                    "tags": gx.tags,
                    "turns": gx.turns,
                    "gold": {
                        "owner": gx.owner,
                        "deadline": str(gx.deadline),
                        "status": gx.status,
                    },
                    "pred": {
                        "owner": px.owner,
                        "owner_raw": px.owner_raw,
                        "deadline": str(px.deadline),
                        "deadline_raw": px.deadline_raw,
                        "status": px.status,
                        "options": [str(d) for d in px.deadline_options],
                        "flags": px.flags,
                    },
                }
            )
        else:
            c["act_full_ok"] += 1
            for t in gx.tags:
                ms.tags[t]["full"] += 1

    if not g.action_items:
        c["neg_meetings"] += 1
        c["neg_pred_actions"] += len(p_acts)

    # ---- decisions, follow-ups ----
    for kind, pre, G, P, gt, pt in [
        (
            "decision",
            "dec",
            g.decisions,
            pred.decisions,
            lambda x: x.summary,
            lambda x: x.summary,
        ),
        (
            "follow_up",
            "fu",
            g.follow_ups,
            pred.follow_ups,
            lambda x: x.topic,
            lambda x: x.topic,
        ),
    ]:
        for x in run_kind(kind, pre, G, P, gt, pt):
            for t in G[x.gold_i].tags:
                ms.tags[t]["full"] += 1

    # ---- questions ----
    qpairs = run_kind(
        "question",
        "q",
        g.open_questions,
        pred.questions,
        lambda x: x.question,
        lambda x: x.question,
    )
    c["q_unres_gold"] += sum(1 for x in g.open_questions if not x.answered)
    c["q_unres_pred"] += sum(1 for x in pred.questions if not x.answered)

    for x in qpairs:
        gx, px = g.open_questions[x.gold_i], pred.questions[x.pred_i]
        c["q_matched"] += 1

        if px.answered == gx.answered:
            c["q_ans_ok"] += 1
            for t in gx.tags:
                ms.tags[t]["full"] += 1
        else:
            det["bad"].append(
                {
                    "type": "bad",
                    "kind": "question",
                    "id": gx.gold_id,
                    "text": gx.question,
                    "pred_text": px.question,
                    "issues": ["answered"],
                    "tags": gx.tags,
                    "turns": gx.turns,
                    "gold": {"answered": gx.answered},
                    "pred": {"answered": px.answered},
                }
            )

        if not gx.answered and not px.answered:
            c["q_unres_hit"] += 1

    # ---- grounding audit: applied identically to every system,
    # whatever its own guardrails ----
    n, bad = _ungrounded(
        p_acts + pred.decisions + pred.questions + pred.follow_ups,
        turns,
    )
    c["ev_items"] += n
    c["ev_ungrounded"] += bad

    # ---- pipeline self-report ----
    r = pred.report or {}
    c["rep_raw"] += sum((r.get("raw_counts") or {}).values())
    c["rep_rejected_ungrounded"] += (r.get("rejected") or {}).get("ungrounded_evidence", 0)
    ak = r.get("attempt_kinds") or {}
    c["rep_attempts"] += sum(ak.values())
    c["rep_bad_attempts"] += sum(
        v for k, v in ak.items() if k in ("invalid_json", "schema", "llm_error")
    )
    c["rep_repairs"] += r.get("repairs", 0)
    c["rep_chunks"] += r.get("chunks", 0)
    c["rep_failed_chunks"] += len(r.get("failed_chunks", []))
    return ms


# ---------------- aggregation ----------------
def aggregate(scores: list[MeetingScore]) -> Counter:
    total: Counter = Counter()
    for s in scores:
        total.update(s.counts)
    return total


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None
    return p, r, f


def _div(a, b):
    return a / b if b else None


def metrics(c: Counter) -> dict:
    m = {}
    m["act_p"], m["act_r"], m["act_f1"] = _prf(c["act_tp"], c["act_fp"], c["act_fn"])
    m["dec_p"], m["dec_r"], m["dec_f1"] = _prf(c["dec_tp"], c["dec_fp"], c["dec_fn"])
    m["q_p"], m["q_r"], m["q_f1"] = _prf(c["q_tp"], c["q_fp"], c["q_fn"])
    m["fu_p"], m["fu_r"], m["fu_f1"] = _prf(c["fu_tp"], c["fu_fp"], c["fu_fn"])
    m["act_owner_acc"] = _div(c["act_owner_ok"], c["act_matched"])
    m["act_dl_acc"] = _div(c["act_dl_ok"], c["act_matched"])
    m["act_dl_lenient"] = _div(c["act_dl_lenient_ok"], c["act_matched"])
    m["act_status_acc"] = _div(c["act_status_ok"], c["act_matched"])
    m["act_full_recall"] = _div(c["act_full_ok"], c["act_tp"] + c["act_fn"])
    m["q_ans_acc"] = _div(c["q_ans_ok"], c["q_matched"])
    m["q_unres_recall"] = _div(c["q_unres_hit"], c["q_unres_gold"])
    m["q_unres_precision"] = _div(c["q_unres_hit"], c["q_unres_pred"])
    m["ungrounded_rate"] = _div(c["ev_ungrounded"], c["ev_items"])
    m["raw_halluc_rate"] = _div(c["rep_rejected_ungrounded"], c["rep_raw"])
    m["schema_fail_rate"] = _div(c["rep_bad_attempts"], c["rep_attempts"])
    m["repairs_per_meeting"] = _div(c["rep_repairs"], c["meetings"])
    m["incomplete_rate"] = _div(c["incomplete"], c["meetings"])
    m["sys_fail_rate"] = _div(c["sys_failed"], c["meetings"])
    m["neg_fp_per_meeting"] = _div(c["neg_pred_actions"], c["neg_meetings"])
    return m


def bootstrap_ci(
    scores: list[MeetingScore],
    key: str,
    n: int = 1000,
    seed: int = 0,
):
    """95% CI by resampling whole meetings (the unit of independence)."""
    if len(scores) < 2:
        return None
    rng = random.Random(seed)
    vals = []

    for _ in range(n):
        sample = [scores[rng.randrange(len(scores))] for _ in scores]
        v = metrics(aggregate(sample))[key]
        if v is not None:
            vals.append(v)

    if len(vals) < n // 2:
        return None

    vals.sort()
    return (
        vals[int(0.025 * len(vals))],
        vals[min(len(vals) - 1, int(0.975 * len(vals)))],
    )


def paired_bootstrap(
    a: list[MeetingScore],
    b: list[MeetingScore],
    key: str,
    n: int = 1000,
    seed: int = 0,
):
    """Distribution of metric(b) - metric(a) over the same resampled meetings."""
    ids = sorted({s.meeting_id for s in a} & {s.meeting_id for s in b})
    if len(ids) < 2:
        return None

    da = {s.meeting_id: s for s in a}
    db = {s.meeting_id: s for s in b}
    rng = random.Random(seed)
    diffs = []

    for _ in range(n):
        pick = [ids[rng.randrange(len(ids))] for _ in ids]
        va = metrics(aggregate([da[i] for i in pick]))[key]
        vb = metrics(aggregate([db[i] for i in pick]))[key]

        if va is not None and vb is not None:
            diffs.append(vb - va)

    if len(diffs) < n // 2:
        return None

    diffs.sort()
    point_a = metrics(aggregate([da[i] for i in ids]))[key]
    point_b = metrics(aggregate([db[i] for i in ids]))[key]

    if point_a is None or point_b is None:
        return None

    return (
        point_b - point_a,
        diffs[int(0.025 * len(diffs))],
        diffs[min(len(diffs) - 1, int(0.975 * len(diffs)))],
    )
