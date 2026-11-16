import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "tests/replay_cache"
THRESH = ROOT / "eval_thresholds.json"

MIN_KEYS = [
    "act_f1",
    "act_r",
    "act_full_recall",
    "act_owner_acc",
    "act_dl_acc",
    "dec_f1",
    "q_unres_recall",
]

MAX_KEYS = [
    "ungrounded_rate",
    "neg_fp_per_meeting",
]

MARGIN = 0.03


def main() -> int:
    write = "--write-thresholds" in sys.argv
    man = json.loads((CACHE / "MANIFEST.json").read_text())

    from copilot.config import settings

    setattr(settings, f"{man['provider']}_model", man["model"])

    from copilot.eval.runner import (
        RUNS,
        RunSpec,
        load_scores,
        run_system,
    )
    from copilot.eval.score import (
        ScoreConfig,
        aggregate,
        metrics,
    )

    shutil.rmtree(RUNS / "ci", ignore_errors=True)

    run_system(
        RunSpec(
            name="ci",
            split=man["split"],
            provider=man["provider"],
            cache_mode="replay",
            cache_dir=str(CACHE),
            log=False,
            pipeline=man["pipeline"],
        )
    )

    scores = load_scores(
        "ci",
        man["split"],
        ScoreConfig(),
    )

    c = aggregate(scores)
    m = metrics(c)

    if c["sys_failed"] or c["incomplete"]:
        print(
            "STALE REPLAY CACHE: some meetings could not be replayed "
            "(a prompt, chunking or model setting changed). "
            "Re-record: python -m copilot.eval.cli run --name rec "
            "--provider "
            f"{man['provider']} --cache live --freeze  "
            "(see docs/ci.md)"
        )
        return 2

    rows = [
        "| metric | value | threshold |",
        "|---|---|---|",
    ]

    if write:
        th = {
            "min": {k: round(max(0.0, m[k] - MARGIN), 3) for k in MIN_KEYS if m[k] is not None},
            "max": {k: round(m[k] + MARGIN, 3) for k in MAX_KEYS if m[k] is not None},
        }

        THRESH.write_text(json.dumps(th, indent=1))
        print("wrote", THRESH, th)
        return 0

    th = json.loads(THRESH.read_text())
    bad = []

    for k, floor in th["min"].items():
        ok = m[k] is not None and m[k] >= floor
        value = f"{m[k]:.3f}" if m[k] is not None else "N/A"
        rows.append(f"| {k} | {value} | ≥ {floor} {'✅' if ok else '❌'} |")

        if not ok:
            bad.append(f"{k}={m[k]} < {floor}")

    for k, ceil in th["max"].items():
        ok = m[k] is None or m[k] <= ceil
        value = f"{m[k]:.3f}" if m[k] is not None else "N/A"
        rows.append(f"| {k} | {value} | ≤ {ceil} {'✅' if ok else '❌'} |")

        if not ok:
            bad.append(f"{k}={m[k]} > {ceil}")

    summary = "## Replay eval (dev split, recorded LLM responses)\n\n" + "\n".join(rows)

    print(summary)

    if os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(summary)

    if bad:
        print("\nREGRESSION:", "; ".join(bad))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
