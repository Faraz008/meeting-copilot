import argparse
import json
import os
import shutil
import statistics
import sys
import time
from pathlib import Path

from copilot.eval.errors import write_errors
from copilot.eval.report import (
    PRIMARY,
    comparison_md,
    diff_md,
    summary_md,
)
from copilot.eval.runner import (
    RUNS,
    RunSpec,
    git_info,
    load_manifest,
    load_scores,
    run_system,
)
from copilot.eval.score import ScoreConfig, aggregate, metrics
from copilot.io import ROOT


def guard(split: str, args) -> None:
    if split != "test":
        return

    if not (getattr(args, "final", False) and os.environ.get("ALLOW_TEST") == "1"):
        sys.exit(
            "Refusing: the test split is frozen (data/SPLITS.md). "
            "Week 5 only: "
            "ALLOW_TEST=1 python -m copilot.eval.cli ... --final"
        )

    with (ROOT / "docs/test_access.log").open(
        "a",
        encoding="utf-8",
    ) as f:
        f.write(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{git_info()['sha']}\t{' '.join(sys.argv[1:])}\n"
        )


def pick_matcher(names: list[str], requested: str) -> str:
    if requested != "auto":
        return requested

    return "title" if any(load_manifest(n)["system"] == "baseline" for n in names) else "turns"


def score_cfg(a, matcher: str) -> ScoreConfig:
    return ScoreConfig(
        use_turns=matcher == "turns",
        min_conf=getattr(a, "min_conf", 0.0),
        exclude_proposed=getattr(a, "exclude_proposed", False),
    )


def cmd_run(a):
    guard(a.split, a)

    pipeline = {
        "extract_prompt": a.prompt,
        "use_grounding": not a.no_grounding,
        "use_pass2": not a.no_pass2,
        "date_resolver": a.date_resolver,
        "filter_completed": a.filter_completed,
    }

    if a.max_chars:
        pipeline["max_chars"] = a.max_chars

    spec = RunSpec(
        name=a.name,
        system=a.system,
        split=a.split,
        provider=a.provider,
        cache_mode=a.cache,
        cache_dir=a.cache_dir,
        resume=a.resume,
        limit=a.limit,
        baseline_prompt=a.baseline_prompt,
        pipeline=pipeline,
    )

    run_system(spec)

    if a.freeze:
        from copilot.llm.cache import CachingProvider

        dest = ROOT / "tests/replay_cache"
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True)

        for p in CachingProvider.used:
            shutil.copy(p, dest / Path(p).name)

        man = load_manifest(a.name)

        (dest / "MANIFEST.json").write_text(
            json.dumps(
                {
                    "provider": a.provider,
                    "model": dict(man["models"])[a.provider],
                    "split": a.split,
                    "pipeline": pipeline,
                    "recorded": man["finished"],
                    "git": man["git"],
                    "files": len(CachingProvider.used),
                },
                indent=1,
            ),
            encoding="utf-8",
        )

        print(f"froze {len(CachingProvider.used)} cache files into {dest}")

    print(f"done: {RUNS / a.name}")


def cmd_score(a):
    guard(a.split, a)

    matcher = pick_matcher([a.name], a.matcher)

    if a.sweep_conf:
        print("min_conf | act_P | act_R | act_F1 | full-correct recall")

        for th in (0.0, 0.3, 0.5, 0.7, 0.9):
            a.min_conf = th

            m = metrics(
                aggregate(
                    load_scores(
                        a.name,
                        a.split,
                        score_cfg(a, matcher),
                    )
                )
            )

            print(
                f"{th:8} | "
                + " | ".join(
                    f"{(m[k] or 0) * 100:5.0f}%"
                    for k in (
                        "act_p",
                        "act_r",
                        "act_f1",
                        "act_full_recall",
                    )
                )
            )

        return

    scores = load_scores(
        a.name,
        a.split,
        score_cfg(a, matcher),
    )

    out = ROOT / "docs/results"
    out.mkdir(parents=True, exist_ok=True)

    text = summary_md(
        a.name,
        scores,
        matcher,
        load_manifest(a.name),
    )

    (out / f"{a.name}.md").write_text(
        text,
        encoding="utf-8",
    )

    (out / f"{a.name}_diff.md").write_text(
        diff_md(scores),
        encoding="utf-8",
    )

    print(text)
    print(f"diffs: {out / (a.name + '_diff.md')}")


def cmd_compare(a):
    guard(a.split, a)

    matcher = pick_matcher(a.names, a.matcher)
    cfg = score_cfg(a, matcher)

    runs = {n: load_scores(n, a.split, cfg) for n in a.names}

    keys = [
        (label, k)
        for label, k in PRIMARY
        if k
        in {
            "act_f1",
            "act_p",
            "act_r",
            "act_full_recall",
            "act_owner_acc",
            "act_dl_acc",
            "dec_f1",
            "q_unres_recall",
            "ungrounded_rate",
            "neg_fp_per_meeting",
        }
    ]

    text = comparison_md(
        runs,
        a.ref or a.names[0],
        keys,
        matcher,
    )

    print(text)

    if a.out:
        Path(a.out).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        Path(a.out).write_text(
            text,
            encoding="utf-8",
        )


def cmd_errors(a):
    guard(a.split, a)

    matcher = pick_matcher([a.name], a.matcher)

    scores = load_scores(
        a.name,
        a.split,
        score_cfg(a, matcher),
    )

    tally = write_errors(
        scores,
        ROOT / f"docs/errors/{a.name}.csv",
    )

    for cat, n in tally.most_common():
        print(f"{n:4}  {cat}")

    print(f"\nwrote docs/errors/{a.name}.csv. Fill in the manual_category by own.")


def cmd_variance(a):
    matcher = pick_matcher(a.names, a.matcher)

    ms = [
        metrics(
            aggregate(
                load_scores(
                    n,
                    a.split,
                    score_cfg(a, matcher),
                )
            )
        )
        for n in a.names
    ]

    print(f"{len(ms)} repeated runs. Anything smaller than ~2 sd between two configs is noise.")

    for label, k in PRIMARY[:9]:
        vals = [m[k] for m in ms if m[k] is not None]

        if len(vals) > 1:
            print(
                f"{label:34} "
                f"mean {100 * statistics.mean(vals):5.1f}%  "
                f"sd {100 * statistics.stdev(vals):4.1f}  "
                f"range {100 * min(vals):.0f}-"
                f"{100 * max(vals):.0f}%"
            )


def main():
    ap = argparse.ArgumentParser(prog="copilot-eval")
    sub = ap.add_subparsers(
        dest="cmd",
        required=True,
    )

    r = sub.add_parser("run")
    r.add_argument("--name", required=True)
    r.add_argument(
        "--system",
        choices=["pipeline", "baseline"],
        default="pipeline",
    )
    r.add_argument(
        "--split",
        choices=["dev", "test"],
        default="dev",
    )
    r.add_argument(
        "--provider",
        required=True,
        help="pin ONE provider; fallback chains confound comparisons",
    )
    r.add_argument(
        "--cache",
        choices=["off", "live", "replay"],
        default="live",
    )
    r.add_argument("--cache-dir")
    r.add_argument("--prompt", default="extract_v1")
    r.add_argument(
        "--baseline-prompt",
        default="baseline_v1",
    )
    r.add_argument(
        "--no-grounding",
        action="store_true",
    )
    r.add_argument(
        "--no-pass2",
        action="store_true",
    )
    r.add_argument(
        "--date-resolver",
        choices=["rules", "dateparser"],
        default="rules",
    )
    r.add_argument(
        "--filter-completed",
        action="store_true",
    )
    r.add_argument("--max-chars", type=int)
    r.add_argument("--resume", action="store_true")
    r.add_argument("--limit", type=int)
    r.add_argument("--final", action="store_true")
    r.add_argument(
        "--freeze",
        action="store_true",
        help=("copy used cache files to tests/replay_cache (Day 15)"),
    )
    r.set_defaults(fn=cmd_run)

    def common(p):
        p.add_argument(
            "--split",
            choices=["dev", "test"],
            default="dev",
        )
        p.add_argument(
            "--matcher",
            choices=["auto", "turns", "title"],
            default="auto",
        )
        p.add_argument(
            "--min-conf",
            type=float,
            default=0.0,
        )
        p.add_argument(
            "--exclude-proposed",
            action="store_true",
        )
        p.add_argument("--final", action="store_true")

    s = sub.add_parser("score")
    s.add_argument("--name", required=True)
    s.add_argument(
        "--sweep-conf",
        action="store_true",
    )
    common(s)
    s.set_defaults(fn=cmd_score)

    c = sub.add_parser("compare")
    c.add_argument(
        "--names",
        nargs="+",
        required=True,
    )
    c.add_argument("--ref")
    c.add_argument("--out")
    common(c)
    c.set_defaults(fn=cmd_compare)

    e = sub.add_parser("errors")
    e.add_argument("--name", required=True)
    common(e)
    e.set_defaults(fn=cmd_errors)

    v = sub.add_parser("variance")
    v.add_argument(
        "--names",
        nargs="+",
        required=True,
    )
    common(v)
    v.set_defaults(fn=cmd_variance)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
