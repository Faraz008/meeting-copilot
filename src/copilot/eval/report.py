from collections import Counter, defaultdict

from copilot.eval.score import (
    aggregate,
    bootstrap_ci,
    metrics,
    paired_bootstrap,
)

PRIMARY = [
    ("Action F1", "act_f1"),
    ("Action precision", "act_p"),
    ("Action recall", "act_r"),
    ("Fully-correct actions (recall)", "act_full_recall"),
    ("Owner accuracy", "act_owner_acc"),
    ("Deadline accuracy", "act_dl_acc"),
    ("Deadline (ambiguity-lenient)", "act_dl_lenient"),
    ("Status accuracy", "act_status_acc"),
    ("Decision F1", "dec_f1"),
    ("Question F1", "q_f1"),
    ("Unresolved-question recall", "q_unres_recall"),
    ("Unresolved-question precision", "q_unres_precision"),
    ("Ungrounded items in output", "ungrounded_rate"),
    ("Raw hallucination rate (pre-filter)", "raw_halluc_rate"),
    ("Spurious actions / negative meeting", "neg_fp_per_meeting"),
    ("Schema/JSON failure rate", "schema_fail_rate"),
    ("Repairs / meeting", "repairs_per_meeting"),
    ("Incomplete runs", "incomplete_rate"),
]

COUNT_KEYS = {"neg_fp_per_meeting", "repairs_per_meeting"}


def fmt(k: str, v) -> str:
    if v is None:
        return "–"
    return f"{v:.1f}" if k in COUNT_KEYS else f"{100 * v:.0f}%"


def cell(k: str, scores) -> str:
    v = metrics(aggregate(scores))[k]
    ci = bootstrap_ci(scores, k)

    if v is None or ci is None:
        return fmt(k, v)

    return f"{fmt(k, v)} [{fmt(k, ci[0])}–{fmt(k, ci[1])}]"


def summary_md(
    name: str,
    scores,
    matcher: str,
    manifest: dict | None = None,
) -> str:
    c = aggregate(scores)

    L = [
        f"# {name}",
        "",
        (
            f"matcher: **{matcher}** · meetings: {len(scores)} · "
            f"gold actions: {c['act_tp'] + c['act_fn']} · "
            f"predicted actions: {c['act_tp'] + c['act_fp']}"
        ),
    ]

    if manifest:
        L.append(
            f"system: {manifest.get('system')} · "
            f"models: {manifest.get('models')} · "
            f"git: {manifest.get('git')} · "
            f"prompt sha: {manifest.get('prompt_sha')}"
        )

    L += [
        "",
        "| metric | value [95% CI over meetings] |",
        "|---|---|",
    ]

    L += [f"| {label} | {cell(k, scores)} |" for label, k in PRIMARY]

    L += [
        "",
        (
            f"Deadline errors on matched actions: "
            f"missing {c['dl_missing']}, "
            f"invented {c['dl_invented']}, "
            f"wrong value {c['dl_wrong']}."
        ),
    ]

    tags = defaultdict(Counter)

    for s in scores:
        for t, cc in s.tags.items():
            tags[t].update(cc)

    L += [
        "",
        "## Hard cases (per tag)",
        "",
        "| tag | n | found | fully correct |",
        "|---|---|---|---|",
    ]

    for t in sorted(tags):
        n = tags[t]["n"]
        L.append(f"| {t} | {n} | {tags[t]['hit']}/{n} | {tags[t]['full']}/{n} |")

    L += [
        "",
        "## Per meeting",
        "",
        ("| meeting | actions TP/FP/FN | decisions TP/FP/FN | questions TP/FP/FN | mismatches |"),
        "|---|---|---|---|---|",
    ]

    for s in scores:
        k = s.counts

        L.append(
            f"| {s.meeting_id} | "
            f"{k['act_tp']}/{k['act_fp']}/{k['act_fn']} | "
            f"{k['dec_tp']}/{k['dec_fp']}/{k['dec_fn']} | "
            f"{k['q_tp']}/{k['q_fp']}/{k['q_fn']} | "
            f"{len(s.details['bad'])} |"
        )

    return "\n".join(L) + "\n"


def diff_md(scores) -> str:
    L = ["# Per-meeting diffs", ""]

    for s in scores:
        d = s.details

        if not (d["fn"] or d["fp"] or d["bad"]):
            continue

        L += [f"## {s.meeting_id}", ""]

        for r in d["fn"]:
            L.append(
                f"- **MISSED** {r['kind']} `{r['id']}` "
                f"turns {r['turns']} tags {r['tags']}: "
                f"{r['text']}"
                + (f"  _(nearby prediction: {r['near_pred']})_" if r.get("near_pred") else "")
            )

        for r in d["fp"]:
            L.append(
                f"- **EXTRA** {r['kind']} turns {r['turns']} "
                f"[{r.get('status')}]: {r['text']}"
                f"  _evidence: {r['quotes'][:140]}_"
            )

        for r in d["bad"]:
            L.append(
                f"- **WRONG {'/'.join(r['issues'])}** "
                f"`{r['id']}` {r['text']}: "
                f"gold={r['gold']} pred={r['pred']}"
            )

        L.append("")

    return "\n".join(L)


def comparison_md(
    runs: dict,
    ref: str,
    keys: list,
    matcher: str,
) -> str:
    names = list(runs)

    L = [
        (
            f"Matcher: **{matcher}**. Values are micro-averaged "
            f"over {len(runs[ref])} meetings; "
            "brackets are 95% bootstrap CIs over meetings."
        ),
        "",
        "| system | " + " | ".join(label for label, _ in keys) + " |",
        "|---|" + "---|" * len(keys),
    ]

    for n in names:
        L.append(f"| {n} | " + " | ".join(cell(k, runs[n]) for _, k in keys) + " |")

    L += [
        "",
        (
            f"### Difference vs `{ref}` "
            "(paired bootstrap; if the interval includes 0, "
            "treat as noise)"
        ),
        "",
        "| system | " + " | ".join(label for label, _ in keys) + " |",
        "|---|" + "---|" * len(keys),
    ]

    for n in names:
        if n == ref:
            continue

        cells = []

        for _, k in keys:
            r = paired_bootstrap(runs[ref], runs[n], k)

            if r is None:
                cells.append("–")
            else:
                d, lo, hi = r
                scale = 1 if k in COUNT_KEYS else 100

                cells.append(f"{scale * d:+.1f} [{scale * lo:+.1f}, {scale * hi:+.1f}]")

        L.append(f"| {n} | " + " | ".join(cells) + " |")

    return "\n".join(L) + "\n"
