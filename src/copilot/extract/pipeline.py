import time
from collections import Counter
from dataclasses import dataclass

from rapidfuzz import fuzz

from copilot.extract.pass1 import run_pass1
from copilot.extract.raw_models import ActionCand
from copilot.extract.reconcile import (
    SOCIAL,
    apply_supersession,
    dedupe,
    first_turn,
    judge_decisions,
    judge_questions,
    merge_competing,
    preresolve_owners,
    same_commitment,
)
from copilot.models import (
    ActionItem,
    Decision,
    Evidence,
    ExtractionResult,
    FollowUp,
    Meeting,
    OpenQuestion,
    stable_id,
)
from copilot.parsers.transcript import build_roster
from copilot.resolve.deadlines import (
    resolve_deadline,
    resolve_deadline_naive,
)
from copilot.resolve.flags import action_flags
from copilot.resolve.priority import priority
from copilot.validate.grounding import norm

CONF = {
    "high": 0.9,
    "medium": 0.6,
    "low": 0.3,
}


@dataclass
class PipelineConfig:
    extract_prompt: str = "extract_v1"
    max_chars: int = 8000
    overlap: int = 4
    date_order: str = "DMY"
    use_grounding: bool = True  # Ablation switches for Week 3.
    use_pass2: bool = True
    date_resolver: str = "rules"  # "rules" | "dateparser"


@dataclass
class RunOutput:
    result: ExtractionResult
    report: dict


def _ids(kind: str, meeting_id: str, cands) -> dict[int, str]:
    used: Counter = Counter()
    out = {}

    for c in cands:
        ft = first_turn(c)
        out[id(c)] = stable_id(
            kind,
            meeting_id,
            ft,
            used[ft],
        )
        used[ft] += 1

    return out


def _dedupe_simple(cands, key):
    return dedupe(
        cands,
        lambda a, b: (
            fuzz.token_set_ratio(
                norm(key(a)),
                norm(key(b)),
            )
            >= 80
            and any(abs(x.turn_idx - y.turn_idx) <= 1 for x in a.evidence for y in b.evidence)
        ),
    )


def run_pipeline(
    meeting: Meeting,
    router,
    cfg: PipelineConfig | None = None,
) -> RunOutput:
    cfg = cfg or PipelineConfig()
    t0 = time.time()

    if not meeting.roster:
        meeting = meeting.model_copy(
            update={
                "roster": build_roster(meeting.turns),
            }
        )

    p1 = run_pass1(
        router,
        meeting,
        prompt_name=cfg.extract_prompt,
        max_chars=cfg.max_chars,
        overlap=cfg.overlap,
        ground=cfg.use_grounding,
    )

    degraded: list[str] = []

    # ---- action items ----
    acts: list[ActionCand] = list(p1.actions)

    for i, c in enumerate(acts):
        c.uid = i + 1

    preresolve_owners(acts, meeting)

    if cfg.use_pass2:
        acts = dedupe(acts, same_commitment)
        apply_supersession(acts)
        acts = merge_competing(acts)

    acts.sort(
        key=lambda c: (
            first_turn(c),
            c.title,
        )
    )

    action_ids = _ids(
        "act",
        meeting.meeting_id,
        acts,
    )

    uid_to_id = {c.uid: action_ids[id(c)] for c in acts}

    resolver = resolve_deadline if cfg.date_resolver == "rules" else resolve_deadline_naive

    final_actions: list[ActionItem] = []

    for c in acts:
        res = (
            resolver(
                c.deadline_raw,
                meeting.date,
                cfg.date_order,
            )
            if c.deadline_raw
            else None
        )

        quotes = " ".join(e.quote for e in c.evidence) + " " + (c.deadline_raw or "")

        conf = CONF[c.confidence] - (
            0.15 if "ungrounded_evidence" in [f.value for f in c.flags] else 0
        )

        final_actions.append(
            ActionItem(
                id=action_ids[id(c)],
                title=c.title,
                owner_raw=c.owner_raw,
                owner=c.owner,
                deadline_raw=c.deadline_raw,
                deadline=res.resolved_date if res else None,
                deadline_time=res.resolved_time if res else None,
                deadline_options=res.options if res else [],
                status=c.status,
                condition=c.condition,
                confidence=max(0.05, conf),
                evidence=[Evidence(**e.model_dump()) for e in c.evidence],
                flags=action_flags(
                    status=c.status,
                    owner=c.owner,
                    deadline_raw=c.deadline_raw,
                    deadline_status=(res.status if res else None),
                    condition=c.condition,
                    confidence_label=c.confidence,
                    existing=c.flags,
                ),
                superseded_by=uid_to_id.get(c.superseded_by_uid),
                owner_candidates=c.owner_candidates,
                priority=priority(
                    quotes,
                    res.resolved_date if res else None,
                    meeting.date,
                ),
            )
        )

    # ---- decisions ----
    ds = sorted(
        (
            _dedupe_simple(
                p1.decisions,
                lambda d: d.summary,
            )
            if cfg.use_pass2
            else p1.decisions
        ),
        key=first_turn,
    )

    dec_ids = _ids(
        "dec",
        meeting.meeting_id,
        ds,
    )

    dj, d_deg = judge_decisions(router, meeting, ds) if cfg.use_pass2 else ({}, False)

    if d_deg:
        degraded.append("decision_judging")

    final_decisions = []

    for i, d in enumerate(ds):
        j = dj.get(i)

        final_decisions.append(
            Decision(
                id=dec_ids[id(d)],
                summary=d.summary,
                rationale=d.rationale,
                confidence=CONF[d.confidence],
                evidence=(
                    [Evidence(**e.model_dump()) for e in d.evidence]
                    + ([j["evidence"]] if j else [])
                ),
                flags=d.flags,
                status=(j["status"] if j else "active"),
                superseded_by=(dec_ids[id(ds[j["by"]])] if j and j["by"] is not None else None),
            )
        )

    # ---- questions ----
    qs = [q for q in p1.questions if not SOCIAL.search(q.question)]

    qs = sorted(
        (
            _dedupe_simple(
                qs,
                lambda q: q.question,
            )
            if cfg.use_pass2
            else qs
        ),
        key=first_turn,
    )

    q_ids = _ids(
        "que",
        meeting.meeting_id,
        qs,
    )

    qj, q_deg = judge_questions(router, meeting, qs) if cfg.use_pass2 and qs else ({}, False)

    if q_deg:
        degraded.append("question_judging")

    final_questions = []
    final_followups = []

    for i, q in enumerate(qs):
        j = qj.get(
            i,
            {
                "status": "unanswered",
                "summary": None,
                "evidence": None,
            },
        )

        ev = [Evidence(**e.model_dump()) for e in q.evidence] + (
            [j["evidence"]] if j["evidence"] else []
        )

        if j["status"] == "deferred":
            # Per labeling guide: deferral is a follow-up,
            # not an unresolved question.
            final_followups.append(
                FollowUp(
                    id=stable_id(
                        "fol",
                        meeting.meeting_id,
                        first_turn(q),
                        1,
                    ),
                    topic=f"Pending: {q.question}"[:200],
                    evidence=ev,
                )
            )
        else:
            final_questions.append(
                OpenQuestion(
                    id=q_ids[id(q)],
                    question=q.question,
                    asked_by=q.asked_by,
                    answered=j["status"] == "answered",
                    answer_summary=j["summary"],
                    evidence=ev,
                )
            )

    # ---- follow-ups ----
    fs = sorted(
        (
            _dedupe_simple(
                p1.followups,
                lambda f: f.topic,
            )
            if cfg.use_pass2
            else p1.followups
        ),
        key=first_turn,
    )

    f_ids = _ids(
        "fol",
        meeting.meeting_id,
        fs,
    )

    final_followups += [
        FollowUp(
            id=f_ids[id(f)],
            topic=f.topic,
            evidence=[Evidence(**e.model_dump()) for e in f.evidence],
        )
        for f in fs
    ]

    result = ExtractionResult(
        action_items=final_actions,
        decisions=final_decisions,
        open_questions=final_questions,
        follow_ups=final_followups,
    )

    raw_total = sum(p1.raw_counts.values())

    rej = Counter(r["reason"] for r in p1.rejected)

    report = {
        "meeting_id": meeting.meeting_id,
        "complete": (not p1.failed_chunks and not degraded),
        "failed_chunks": p1.failed_chunks,
        "degraded": degraded,
        "chunks": p1.n_chunks,
        "prompt": {
            "name": cfg.extract_prompt,
            "sha": p1.prompt_sha,
        },
        "raw_counts": p1.raw_counts,
        "rejected": dict(rej),
        "hallucination_rate": (
            round(
                rej.get("ungrounded_evidence", 0) / raw_total,
                3,
            )
            if raw_total
            else 0.0
        ),
        "attempt_kinds": dict(Counter(a["kind"] for a in p1.attempts)),
        "providers_used": dict(Counter(a["provider"] for a in p1.attempts if a["kind"] == "ok")),
        "repairs": sum(1 for a in p1.attempts if a.get("repaired")),
        "seconds": round(
            time.time() - t0,
            1,
        ),
        "config": cfg.__dict__,
    }

    return RunOutput(
        result,
        report,
    )
